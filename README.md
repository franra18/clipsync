# ClipSync 🎬

ClipSync is an AI-powered video clipping tool that turns YouTube links into vertical 9:16 Shorts with auto-framing and subtitles.


## 🛠 Technologies

### Architecture & Infrastructure
* **Docker & Docker Compose**: Complete environment orchestration for local development and production.
* **MinIO**: S3-compatible object storage for managing raw video files and processed clips.
* **Redis**: In-memory message broker used for asynchronous task queue management.

### Backend (`/apps/backend`)
* **Python & FastAPI (Uvicorn)**: High-performance API server managing client requests and job dispatching.
* **OpenCV**: Frame extraction, image preprocessing, and stream transformation.
* **Caffe Deep Learning Framework**: Pre-trained Single Shot MultiBox Detector (SSD) model for real-time subject/face detection.
* **Background Worker**: Asynchronous Python worker process for running deep learning tasks offloaded via Redis.

### Frontend (`/apps/frontend`)
* **React 18 & Vite 5**: Modern, fast web application framework and build tool.
* **Tailwind CSS**: Utility-first CSS framework for responsive styling.
* **Lucide React**: Icon library for modern UI controls.
* **pnpm / Corepack**: Package manager running directly inside Node 20 Alpine containers.


## ⚙️ The Process

1. **Frame Extraction**: The backend streams video input frame-by-frame via OpenCV.
2. **Blob Preprocessing**: Each frame is normalized into a $300 \times 300$ pixel spatial blob image.
3. **Deep Learning Inference**: The preprocessed blob passes through the Caffe SSD neural network to compute bounding box predictions and confidence scores.
4. **Post-Processing & Sync**: Valid detections above confidence thresholds are extracted to trigger clip trimming or downstream synchronization tasks.

## 🚀 Getting Started

### Prerequisites

* [Docker](https://www.docker.com/) and **Docker Compose** installed.

---

### Running the Entire Stack

Because all services (API, Worker, Frontend, Redis, MinIO) are containerized, you can launch the complete ecosystem with a single command:

1. **Clone the repository:**
```bash
git clone [https://github.com/franra18/clipsync.git](https://github.com/franra18/clipsync.git)
cd clipsync
```

2. **Start all services:**
```bash
docker compose up --build
```


3. **Access the services:**
* **Frontend Interface**: [http://localhost:5173](http://localhost:5173)
* **FastAPI Backend / Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **MinIO Console**: [http://localhost:9001](http://localhost:9001) *(Credentials: `admin` / `password123`)*
* **MinIO API**: [http://localhost:9000](http://localhost:9000)
* **Redis Server**: `localhost:6379`


4. **Stopping the Stack:**
```bash
docker compose down
```

## 🎥 Live Demo


https://github.com/user-attachments/assets/b2773925-aaa9-4247-bffb-d2da0eea7dda


