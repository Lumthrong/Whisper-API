FROM python:3.10

ARG CACHE_BUST=1

WORKDIR /app

# 🔥 System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 🔥 HuggingFace cache fix
ENV HF_HOME=/tmp/huggingface

# 🔥 Upgrade pip tools (IMPORTANT)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 🔥 Install torch FIRST (prebuilt CPU wheel)
RUN pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# 🔥 Install requirements using prebuilt binaries ONLY
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy app
COPY . .

# Start server
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
