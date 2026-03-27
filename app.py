from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import tempfile
import os
import uuid
import threading

app = FastAPI()

# Load model once
model = WhisperModel("tiny", compute_type="int8")

# Store jobs
jobs = {}


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):

    job_id = str(uuid.uuid4())

    # Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
        temp.write(await file.read())
        temp_path = temp.name

    jobs[job_id] = {"status": "processing"}

    # 🔥 BACKGROUND PROCESS (THREAD SAFE FOR RENDER)
    def process():
        try:
            print("🚀 Processing started:", job_id)

            # Run Whisper
            segments, _ = model.transcribe(temp_path)

            # 🔥 FORCE FULL EXECUTION (CRITICAL FIX)
            segments_list = list(segments)

            # Save result
            jobs[job_id] = {
                "status": "completed",
                "segments": [
                    {"start": s.start, "text": s.text}
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
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 🔥 DO NOT USE BackgroundTasks (Render issue)
    threading.Thread(target=process).start()

    return {"jobId": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):

    job = jobs.get(job_id)

    if not job:
        return {"status": "failed"}

    # 🔥 Prevent empty / broken responses
    if job.get("status") == "completed" and not job.get("segments"):
        return {"status": "failed"}

    return job