FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-opencv \
    ffmpeg \
    nodejs \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Descargar modelo DNN Face Detector
RUN wget -q https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel -O /app/res10_300x300_ssd_iter_140000.caffemodel \
    && wget -q https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt -O /app/deploy.prototxt

# Fijamos 'av' a la rama compatible 12.x antes de faster-whisper
RUN pip3 install --no-cache-dir --break-system-packages "av>=12.0.0,<13.0.0" yt-dlp faster-whisper

COPY test_clip.py .

CMD ["python3", "test_clip.py"]
