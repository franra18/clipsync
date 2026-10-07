from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="ClipsSync API")

class ClipJobRequest(BaseModel):
    video_url: HttpUrl
    start_time: str  # Formato "02:15"
    end_time: str    # Formato "02:40"
    vertical_reframe: bool = False

@app.post("/api/jobs")
async def create_clip_job(job: ClipJobRequest):
    # 1. Generar un job_id único (UUID)
    # 2. Guardar estado 'PENDING' en Redis
    # 3. Enviar a la cola para que el Worker lo procese
    return {"job_id": "temp-id-123", "status": "QUEUED"}
