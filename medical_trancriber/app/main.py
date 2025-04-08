# app/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.endpoints import websocket_endpoints, medical_endpoints

app = FastAPI(
    title="Medical Transcription API",
    description="Real-time transcription with optimized diarization,soap note generation, and medical data extraction.",
    version="2.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_endpoints.router)
app.include_router(medical_endpoints.router)

if __name__ == "__main__":
    pass