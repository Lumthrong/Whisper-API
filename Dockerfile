FROM python:3.10

ARG CACHE_BUST=1

WORKDIR /app

# 🔥 Install system dependencies (IMPORTANT)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 🔥 Fix HuggingFace cache
ENV HF_HOME=/tmp/huggingface

# 🔥 Install torch FIRST (CRITICAL FIX)
RUN pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# 🔥 Then install rest
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Start server
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
