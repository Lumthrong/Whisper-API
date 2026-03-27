FROM python:3.10

WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Avoid permission/cache issues
ENV HF_HOME=/tmp/huggingface

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Start server (Render compatible)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]