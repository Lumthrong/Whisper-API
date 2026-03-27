from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import tempfile
import os
import uuid
import threading

# ================= ENV =================
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token
else:
    print("⚠️ HF_TOKEN not found")

app = FastAPI()

# ================= MODEL =================
model = None

def get_model():
    global model
    if model is None:
        print("🔄 Loading Whisper model...")
        model = WhisperModel("tiny", compute_type="int8")
    return model

# ================= JOB STORE =================
jobs = {}

# ================= ROUTES =================
@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):

    job_id = str(uuid.uuid4())

    # ✅ FIX: preserve actual file extension
    suffix = os.path.splitext(file.filename)[1] or ".mp3"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    jobs[job_id] = {"status": "processing"}

    # ================= BACKGROUND PROCESS =================
    def process():
        try:
            print("🚀 Processing started:", job_id)

            # ✅ Load model lazily (Render-safe)
            whisper_model = get_model()

            # ✅ Transcribe
            segments, _ = whisper_model.transcribe(temp_path)

            # ✅ Force execution
            segments_list = list(segments)

            print("🧠 Segments count:", len(segments_list))

            # ✅ Fail if empty (no silent bugs)
            if not segments_list:
                raise Exception("No segments returned (likely ffmpeg/format issue)")

            # ✅ Save result
            jobs[job_id] = {
                "status": "completed",
                "segments": [
                    {"start": s.start, "text": s.text.strip()}
                    for s in segments_list
                ]
            }

            print("✅ Processing completed:", job_id)

        except Exception as e:
            print("❌ Processing error:", e)

            jobs[job_id] = {
                "status": "failed",
                "error": str(e)
            }

        finally:
            # ✅ Always cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # ✅ Safer thread for Render
    thread = threading.Thread(target=process)
    thread.daemon = True
    thread.start()

    return {"jobId": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):

    job = jobs.get(job_id)

    if not job:
        return {"status": "failed"}

    # ✅ Prevent fake "completed" with empty data
    if job.get("status") == "completed" and not job.get("segments"):
        return {"status": "failed"}

    return job