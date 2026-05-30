"""
Tennia — Elite Biomechanics AI Coach
FastAPI application entry point.
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers import video, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize CV models on startup."""
    print("🎾 Tennia — Biomechanics AI Coach starting...")
    websocket.init_models()
    print("🚀 Server ready!")
    yield
    print("👋 Shutting down Tennia server.")


app = FastAPI(
    title="Tennia — Tennis Analytics Engine",
    description="Elite-level tennis analytics with real-time computer vision",
    version="0.1.0",
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
        "version": "0.1.0",
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
