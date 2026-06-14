"""
Tennia — Elite Biomechanics AI Coach
FastAPI application entry point.

ARCHITECTURE (Two-Pass):
────────────────────────
1. User uploads a video via POST /api/upload
2. Backend processes the ENTIRE video in a background thread
   (MediaPipe → Kinematics → AI Coach → saves results to .json)
3. Frontend polls /api/status/{id} for progress (or uses WebSocket)
4. Once done, frontend:
   - Plays the video natively via HTML5 <video src="/api/video/{id}">
   - Fetches analysis data from GET /api/analysis/{id}
   - Draws skeleton overlay on a <canvas> synced to video time
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers import video, websocket
from processing.analyzer import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize CV models on startup."""
    print("🎾 Tennia — Biomechanics AI Coach starting...")
    init_models()
    print("🚀 Server ready!")
    yield
    print("👋 Shutting down Tennia server.")


app = FastAPI(
    title="Tennia — Tennis Analytics Engine",
    description="Elite-level tennis analytics with real-time computer vision",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(video.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": "Tennia",
        "version": "0.2.0",
        "architecture": "two-pass",
        "status": "running",
        "description": "Tennis Analytics Engine — Upload a video to get started.",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
