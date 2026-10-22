import json
import time
import redis
from src.core.config import REDIS_HOST, REDIS_PORT
from src.core.storage import ensure_bucket
from src.services.video_processor import process_video_pipeline

QUEUE = "clip_jobs"
PROCESSING = "clip_jobs:processing"

def start_worker():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    ensure_bucket()

    # Devuelve a la cola los trabajos que quedaron a medias si el worker se cayó
    while r.lmove(PROCESSING, QUEUE, "RIGHT", "LEFT"):
        pass

    print(f"🚀 Worker escuchando Redis en {REDIS_HOST}:{REDIS_PORT}...")
    
    while True:
        job_id = None
        # Espera corta: redis-py 8 corta la conexión a los 5 s por defecto (socket_timeout)
        message = r.blmove(QUEUE, PROCESSING, 2, "LEFT", "RIGHT")
        if message is None:
            continue
        try:
            job_data = json.loads(message)
            job_id = job_data["job_id"]
            
            print(f"[{job_id}] Cambiando estado a PROCESSING...")
            r.hset(f"job:{job_id}", "status", "PROCESSING")
            
            # 1. Ejecutar pipeline y obtener la ruta del objeto en MinIO
            object_name = process_video_pipeline(
                job_id=job_id,
                video_url=job_data["video_url"],
                start_time=job_data["start_time"],
                end_time=job_data["end_time"]
            )
            
            # 2. Guardar object_name y marcar como COMPLETED
            r.hset(f"job:{job_id}", mapping={
                "status": "COMPLETED",
                "object_name": object_name
            })
            print(f"[{job_id}] 🎉 Proceso finalizado y marcado como COMPLETED!")
            
        except Exception as e:
            print(f"Error procesando trabajo {job_id or ''}: {e}")
            if job_id:
                r.hset(f"job:{job_id}", mapping={"status": "FAILED", "error": str(e)})
            time.sleep(1)
        finally:
            r.lrem(PROCESSING, 1, message)

if __name__ == "__main__":
    start_worker()
