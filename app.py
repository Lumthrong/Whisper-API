from fastapi import FastAPI, UploadFile, File
import whisper
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
        model = whisper.load_model("tiny")
    return model

# ================= JOB STORE =================
jobs = {}

# ================= ROUTES =================
@app.get("/")
def home():
    return {"status": "ok"}

@app.get("/health")
def health():
    global model
    return {
        "status": "ok",
        "model_loaded": model is not None
    }

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):

    job_id = str(uuid.uuid4())

    suffix = os.path.splitext(file.filename)[1] or ".mp3"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await file.read()

        # 🚨 Skip tiny/broken files early
        if len(content) < 2000:
            return {
                "jobId": job_id,
                "status": "completed",
                "segments": []
            }

        temp.write(content)
        temp_path = temp.name

    jobs[job_id] = {"status": "processing"}

    # ================= BACKGROUND PROCESS =================
    def process():
        try:
            print("🚀 Processing started:", job_id)

            whisper_model = get_model()

            # ✅ Transcribe safely
            result = whisper_model.transcribe(temp_path)

            # 🚨 Validate result
            if not result or "segments" not in result:
                raise Exception("Invalid result from Whisper")

            segments_list = [
                {
                    "start": seg.get("start", 0),
                    "text": seg.get("text", "").strip()
                }
                for seg in result["segments"]
                if seg.get("text", "").strip()
            ]

            print("🧠 Segments count:", len(segments_list))

            # 🚨 Handle empty / silent audio safely
            if not segments_list:
                print("⚠️ No speech detected, skipping")
                jobs[job_id] = {
                    "status": "completed",
                    "segments": []
                }
                return

            jobs[job_id] = {
                "status": "completed",
                "segments": segments_list
            }

            print("✅ Processing completed:", job_id)

        except Exception as e:
            print("⚠️ Skipping bad chunk:", e)

            # 🚨 DO NOT fail pipeline — return empty instead
            jobs[job_id] = {
                "status": "completed",
                "segments": []
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    thread = threading.Thread(target=process)
    thread.daemon = True
    thread.start()

    from fastapi.responses import JSONResponse
    return JSONResponse(content={"jobId": job_id})

@app.get("/status/{job_id}")
def get_status(job_id: str):

    job = jobs.get(job_id)

    if not job:
        return {"status": "failed"}

    return job

@app.on_event("startup")
def load_model_on_startup():
    print("🔥 Preloading Whisper model...")
    get_model()