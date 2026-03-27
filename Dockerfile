FROM python:3.10

ARG CACHE_BUST=1   # 🔥 ADD THIS LINE

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg

ENV HF_HOME=/tmp/huggingface

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
