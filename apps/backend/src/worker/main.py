import json
import time
import redis
from src.core.config import REDIS_HOST, REDIS_PORT
from src.services.video_processor import process_video_pipeline

def start_worker():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    print(f"🚀 Worker escuchando Redis en {REDIS_HOST}:{REDIS_PORT}...")

    while True:
        try:
            _, message = r.blpop("clip_jobs")
            job_data = json.loads(message.decode("utf-8"))
            job_id = job_data["job_id"]

            print(f"[{job_id}] Procesando...")
            r.hset(f"job:{job_id}", "status", "PROCESSING")

            process_video_pipeline(
                job_id=job_id,
                video_url=job_data["video_url"],
                start_time=job_data["start_time"],
                end_time=job_data["end_time"]
            )

            r.hset(f"job:{job_id}", "status", "COMPLETED")
            print(f"[{job_id}] ¡Completado!")

        except Exception as e:
            print(f"Error en worker: {e}")
            if 'job_id' in locals():
                r.hset(f"job:{job_id}", mapping={"status": "FAILED", "error": str(e)})
            time.sleep(1)

if __name__ == "__main__":
    start_worker()
