FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_DIR=/app \
    MODEL_PROTO_PATH=/app/deploy.prototxt \
    MODEL_CAFFE_PATH=/app/res10_300x300_ssd_iter_140000.caffemodel

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modelo DNN Face Detector (versionado en el repo)
COPY deploy.prototxt res10_300x300_ssd_iter_140000.caffemodel ./

COPY src/ ./src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
