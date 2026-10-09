import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
import redis

from src.core.config import REDIS_HOST, REDIS_PORT
from src.core.storage import generate_presigned_download_url

router = APIRouter(prefix="/api/clips", tags=["Clips"])
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

class ClipCreateRequest(BaseModel):
    video_url: HttpUrl
    start_time: str = Field(..., example="00:05")
    end_time: str = Field(..., example="00:15")

class ClipResponse(BaseModel):
    job_id: str
    status: str
    download_url: Optional[str] = None

@router.post("", response_model=ClipResponse, status_code=202)
def create_clip(payload: ClipCreateRequest):
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "video_url": str(payload.video_url),
        "start_time": payload.start_time,
        "end_time": payload.end_time
    }
    
    redis_client.hset(f"job:{job_id}", mapping={"status": "QUEUED"})
    redis_client.rpush("clip_jobs", json.dumps(job_data))
    
    return ClipResponse(job_id=job_id, status="QUEUED")

@router.get("/{job_id}", response_model=ClipResponse)
def get_clip_status(job_id: str):
    job_info = redis_client.hgetall(f"job:{job_id}")
    if not job_info:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")

    status = job_info.get(b"status", b"UNKNOWN").decode("utf-8")
    download_url = None

    if status == "COMPLETED":
        download_url = generate_presigned_download_url(f"clips/{job_id}.mp4")

    return ClipResponse(job_id=job_id, status=status, download_url=download_url)
