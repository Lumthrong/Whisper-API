from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from faster_whisper import WhisperModel
import tempfile
import os
import uuid

app = FastAPI()

# Load model once
model = WhisperModel("base", compute_type="int8")

# Store jobs
jobs = {}

@app.get("/")
def home():
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):

    job_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp:
        temp.write(await file.read())
        temp_path = temp.name

    jobs[job_id] = {"status": "processing"}

    def process():
        try:
            segments, _ = model.transcribe(temp_path)

            jobs[job_id] = {
                "status": "done",
                "segments": [
                    {"start": s.start, "text": s.text}
                    for s in segments
                ]
            }

        except Exception as e:
            jobs[job_id] = {"status": "error", "error": str(e)}

        finally:
            os.remove(temp_path)

    background_tasks.add_task(process)

    return {"jobId": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    return jobs.get(job_id, {"error": "Invalid job ID"})