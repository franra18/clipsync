# 🎬 ClipSync

> **Turn any YouTube video into a vertical 9:16 Short, with face-tracked framing and animated subtitles, in one click.**

ClipSync is a full-stack, containerised video clipping tool. Paste a YouTube link, pick a start and end time, and an asynchronous worker downloads the segment, transcribes it, detects the speaker's face and renders a ready-to-post vertical clip.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-C72E49?style=for-the-badge&logo=minio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## 📑 Table of Contents

- [Demo](#-demo)
- [Features](#-features)
- [How It Works](#️-how-it-works)
- [Architecture](#️-architecture)
- [Tech Stack](#️-tech-stack)
- [API](#-api)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)

---

## 🎥 Demo


https://github.com/user-attachments/assets/b2773925-aaa9-4247-bffb-d2da0eea7dda


---

## ✨ Features

- **🔗 YouTube in, Short out:** paste a link and a time range (`MM:SS` or `HH:MM:SS`). Only that segment is downloaded.
- **📱 Vertical 9:16 output:** 1080 × 1920 MP4 (H.264 + AAC), ready for YouTube Shorts, TikTok or Reels.
- **🙂 Face-tracked framing:** a neural face detector finds the speaker and builds a close-up "facecam" panel.
- **💬 Animated subtitles:** word-level transcription burned into the video in short, punchy 2-word chunks with a pop-in animation.
- **⚡ Asynchronous processing:** jobs are queued in Redis and processed by a background worker, so the API responds instantly.
- **📦 Object storage:** finished clips are stored in MinIO (S3-compatible), downloaded through a presigned URL and deleted automatically after 7 days (`CLIP_RETENTION_DAYS`).
- **🐳 One-command setup:** the whole stack runs with Docker Compose.

---

## ⚙️ How It Works

Each job goes through this pipeline in the worker:

1. **Download:** `yt-dlp` fetches only the requested range (video up to 1440p plus audio), with keyframes forced at the cuts and a near-lossless intermediate encode so the face close-up stays sharp.
2. **Transcribe:** `faster-whisper` (`base` model, CPU, int8) generates word-level timestamps, which are turned into an animated `.ass` subtitle file.
3. **Detect the face:** OpenCV's DNN module runs a Caffe **SSD ResNet-10** face detector (300 × 300 input) on sampled frames and keeps the most confident detection. If no face is found, it falls back to the top-left corner, where stream webcams usually sit.
4. **Render:** FFmpeg stacks two panels into a 1080 × 1920 frame, a lightly sharpened **1080 × 720 face close-up** on top and a **1080 × 1200 view of the full scene** below, and burns in the subtitles.
5. **Store:** the clip is uploaded to MinIO and the job is marked `COMPLETED`. The frontend polls the job and shows the download link.

Job states: `QUEUED` → `PROCESSING` → `COMPLETED` / `FAILED`. If the worker restarts mid-job, the job goes back to the queue. Job state is kept in Redis for 24 hours.

---

## 🏗️ Architecture

```text
┌────────────┐  POST /api/clips   ┌────────────┐   push job    ┌─────────┐
│  Frontend  │ ─────────────────▶ │  FastAPI   │ ────────────▶ │  Redis  │
│ React+Vite │ ◀───────────────── │    API     │ ◀──── status ─│ (queue) │
└────────────┘  GET /{job_id}     └────────────┘               └────┬────┘
      ▲            (polling)            │ presigned URL             │ pop job
      │                                 ▼                           ▼
      │                           ┌────────────┐   upload clip ┌──────────┐
      └──────── download ──────── │   MinIO    │ ◀──────────── │  Worker  │
                                  │ (S3 store) │               │ yt-dlp · │
                                  └────────────┘               │ Whisper ·│
                                                               │ OpenCV · │
                                                               │ FFmpeg   │
                                                               └──────────┘
```

---

## 🛠️ Tech Stack

| Area | Technology |
|---|---|
| **API** | Python 3.11, FastAPI, Uvicorn, Pydantic |
| **Worker** | yt-dlp, faster-whisper, OpenCV DNN (Caffe SSD face detector), FFmpeg |
| **Queue & state** | Redis 7 |
| **Storage** | MinIO (S3-compatible) via `boto3` |
| **Frontend** | React 18, Vite 5, Tailwind CSS, Lucide React |
| **Infrastructure** | Docker, Docker Compose, pnpm (Corepack) on Node 20 Alpine |

---

## 🔌 API

Interactive docs are available at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/clips` | Queues a new clip. Body: `{ "video_url", "start_time", "end_time" }`. Returns `202` with the `job_id`, or `422` if the times are invalid or the end is not after the start. |
| `GET` | `/api/clips/{job_id}` | Returns the job status, the `error` message if it failed and, once completed, a presigned `download_url`. |

```bash
curl -X POST http://localhost:8000/api/clips \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=...", "start_time": "00:05", "end_time": "00:35"}'
```

---

## 📁 Project Structure

```text
clipsync/
├── apps/
│   ├── backend/
│   │   ├── Dockerfile                 # Python 3.11 + FFmpeg + face detector model
│   │   ├── requirements.txt
│   │   ├── tests/test_timecode.py     # Run with: python -m tests.test_timecode
│   │   └── src/
│   │       ├── api/
│   │       │   ├── main.py            # FastAPI app + CORS
│   │       │   └── routes/clips.py    # POST /api/clips, GET /api/clips/{job_id}
│   │       ├── core/
│   │       │   ├── config.py          # Redis, MinIO and clip retention settings
│   │       │   ├── storage.py         # S3 client, bucket setup + presigned URLs
│   │       │   └── timecode.py        # MM:SS / HH:MM:SS parsing and validation
│   │       ├── services/
│   │       │   └── video_processor.py # Download → subtitles → face crop → render → upload
│   │       └── worker/main.py         # Redis job consumer
│   └── frontend/
│       └── src/
│           ├── App.jsx                # Form, job polling and download
│           └── TimeInput.jsx          # MM:SS / HH:MM:SS time input
└── docker-compose.yaml                # api, worker, frontend, redis, minio
```

---

## 🚀 Getting Started

**Requirements:** [Docker](https://www.docker.com/) and Docker Compose.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/franra18/clipsync.git
   cd clipsync
   ```

2. **Start every service:**
   ```bash
   docker compose up --build
   ```

3. **Open the services:**

   | Service | URL |
   |---|---|
   | Frontend | [http://localhost:5173](http://localhost:5173) |
   | API docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |
   | MinIO console | [http://localhost:9001](http://localhost:9001) (`admin` / `password123`) |
   | MinIO API | `http://localhost:9000` |
   | Redis | `localhost:6379` |

   All ports are bound to `127.0.0.1`, so the services are only reachable from your own machine.

   The API reloads on code changes, the worker does not: after editing the pipeline, run `docker compose restart worker`.

4. **Stop the stack:**
   ```bash
   docker compose down
   ```

> ⚠️ The MinIO credentials in `docker-compose.yaml` are for local development only. Change them before deploying anywhere public.

---

<p align="center">Made by <a href="https://github.com/franra18">Francisco Ramírez Cañadas</a></p>
