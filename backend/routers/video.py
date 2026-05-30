"""
Video Upload Router — Handles video file uploads with ffmpeg pre-processing
to fix iPhone rotation metadata before the CV pipeline sees the frames.
"""
import os
import uuid
import shutil
import subprocess
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles

from config import UPLOAD_DIR

router = APIRouter(prefix="/api", tags=["video"])

# Track uploaded videos and their processing status
video_registry: dict = {}


def _fix_rotation(input_path: str) -> str:
    """
    Use ffmpeg to bake iPhone EXIF rotation into actual pixel data.
    iPhone videos store rotation as metadata which OpenCV ignores,
    causing the video to appear sideways.

    Returns the path to the corrected file (always .mp4).
    """
    base, _ = os.path.splitext(input_path)
    output_path = base + "_fixed.mp4"

    # Check if ffmpeg is available
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("⚠️  ffmpeg not found — skipping rotation fix. Install with: brew install ffmpeg")
        return input_path

    try:
        cmd = [
            ffmpeg_path,
            "-i", input_path,
            "-c:v", "libx264",     # Re-encode video (applies rotation)
            "-preset", "fast",      # Faster encoding
            "-crf", "18",           # High quality
            "-c:a", "copy",         # Copy audio as-is
            "-movflags", "+faststart",
            "-y",                   # Overwrite output
            output_path,
        ]
        print(f"🔧 Fixing video rotation: {os.path.basename(input_path)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"⚠️  ffmpeg rotation fix failed: {result.stderr[-500:]}")
            return input_path

        # Remove original, keep the fixed one
        os.remove(input_path)
        print(f"✅ Video rotation fixed: {os.path.basename(output_path)}")
        return output_path

    except subprocess.TimeoutExpired:
        print("⚠️  ffmpeg timed out — using original video")
        return input_path
    except Exception as e:
        print(f"⚠️  ffmpeg error: {e} — using original video")
        return input_path


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file (.mp4, .mov, .avi) for processing.
    Automatically fixes iPhone rotation metadata via ffmpeg.
    Returns a video_id for tracking.
    """
    # Validate file type
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}"
        )

    # Generate unique ID
    video_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{video_id}{ext}")

    # Save file
    try:
        async with aiofiles.open(save_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Fix rotation (blocks briefly but ensures correct frames for CV)
    fixed_path = _fix_rotation(save_path)

    # Register
    video_registry[video_id] = {
        "id": video_id,
        "filename": file.filename,
        "path": fixed_path,
        "status": "uploaded",
        "progress": 0,
        "total_frames": 0,
        "current_frame": 0,
    }

    return JSONResponse({
        "video_id": video_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Video uploaded and pre-processed. Connect to WebSocket to start analysis.",
    })


@router.get("/status/{video_id}")
async def get_status(video_id: str):
    """Get processing status for a video."""
    if video_id not in video_registry:
        raise HTTPException(status_code=404, detail="Video not found")

    info = video_registry[video_id]
    return JSONResponse({
        "video_id": video_id,
        "status": info["status"],
        "progress": info["progress"],
        "total_frames": info["total_frames"],
        "current_frame": info["current_frame"],
    })


@router.get("/videos")
async def list_videos():
    """List all uploaded videos."""
    return JSONResponse({
        "videos": [
            {
                "id": v["id"],
                "filename": v["filename"],
                "status": v["status"],
                "progress": v["progress"],
            }
            for v in video_registry.values()
        ]
    })
