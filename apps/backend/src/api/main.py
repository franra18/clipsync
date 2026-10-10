from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes.clips import router as clips_router

app = FastAPI(title="ClipSync API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clips_router)
