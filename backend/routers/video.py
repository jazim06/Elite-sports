"""
Video Router — Handles uploads, serves video files, and returns analysis data.

TWO-PASS ARCHITECTURE:
──────────────────────
1. POST /api/upload     → Upload video, fix rotation, start background processing
2. GET  /api/status/{id} → Poll processing progress (0-100%)
3. GET  /api/video/{id}  → Serve the actual .mp4 file for HTML5 <video> playback
4. GET  /api/analysis/{id} → Return the full analysis JSON (landmarks, angles, notes)

The frontend uses endpoints 3 and 4 AFTER processing completes.
"""
import os
import uuid
import json
import shutil
import subprocess
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import aiofiles

from config import UPLOAD_DIR
from processing.analyzer import process_video_async

router = APIRouter(prefix="/api", tags=["video"])

# Track uploaded videos and their processing status
video_registry: dict = {}


def _fix_rotation(input_path: str) -> str:
    """
    Use ffmpeg to bake iPhone EXIF rotation into actual pixel data.

    WHY THIS EXISTS:
    iPhone videos store rotation as metadata (e.g., "this video should be
    rotated 90° clockwise"). Most video players read this metadata and rotate
    automatically. But OpenCV (our computer vision library) IGNORES this
    metadata and reads the raw pixels, which are sideways.

    So ffmpeg re-encodes the video, physically rotating every pixel to the
    correct orientation. After this, OpenCV sees an upright video.

    Also adds -movflags +faststart so the browser can start playing
    before the full file downloads.
    """
    base, _ = os.path.splitext(input_path)
    output_path = base + "_fixed.mp4"

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("⚠️  ffmpeg not found — skipping rotation fix. Install with: brew install ffmpeg")
        return input_path

    try:
        cmd = [
            ffmpeg_path,
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-an",  # Strip audio to prevent PCM in MP4 container errors
            "-movflags", "+faststart",  # Lets browser play while downloading
            "-y",
            output_path,
        ]
        print(f"🔧 Fixing video rotation: {os.path.basename(input_path)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print(f"⚠️  ffmpeg failed: {result.stderr[-500:]}")
            return input_path

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
    Upload a video file for processing.

    WHAT HAPPENS:
    1. Saves the file to disk
    2. Runs ffmpeg to fix iPhone rotation
    3. Starts background processing (MediaPipe + kinematics + AI coach)
    4. Returns immediately with a video_id — frontend polls /api/status/{id}
    """
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}"
        )

    video_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{video_id}{ext}")

    # Save uploaded file to disk
    try:
        async with aiofiles.open(save_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Fix rotation (synchronous but fast — ~2-5s for a short clip)
    fixed_path = _fix_rotation(save_path)

    # Register the video
    video_registry[video_id] = {
        "id": video_id,
        "filename": file.filename,
        "path": fixed_path,
        "status": "processing",  # Start processing immediately
        "progress": 0,
        "total_frames": 0,
        "current_frame": 0,
        "analysis_path": None,
    }

    # Start background processing (non-blocking)
    asyncio.create_task(
        process_video_async(fixed_path, video_registry[video_id])
    )

    return JSONResponse({
        "video_id": video_id,
        "filename": file.filename,
        "status": "processing",
        "message": "Video uploaded. Processing started in background. Poll /api/status/{video_id} for progress.",
    })


@router.get("/status/{video_id}")
async def get_status(video_id: str):
    """
    Get processing progress.

    The frontend polls this endpoint every ~500ms to update the progress bar.
    Once status is "completed", the frontend switches to playback mode.
    """
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


@router.get("/video/{video_id}")
async def serve_video(video_id: str):
    """
    Serve the actual .mp4 video file.

    WHY THIS EXISTS:
    The frontend uses a native HTML5 <video> tag which needs a URL to the
    video file. This endpoint serves it directly so the browser can play it
    with its built-in video player — smooth, hardware-accelerated, full fps.

    The browser handles play/pause, seeking, speed control, and buffering
    all by itself. No WebSocket needed!
    """
    if video_id not in video_registry:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = video_registry[video_id]["path"]
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video_id}.mp4",
    )


@router.get("/analysis/{video_id}")
async def get_analysis(video_id: str):
    """
    Return the full analysis JSON for a processed video.

    WHAT'S IN THE JSON:
    - metadata: fps, total frames, duration, processing time
    - frames: array of per-frame data (landmarks_2d, joint_angles, angular_velocity)
    - coaching_notes: array of AI-generated coaching notes with timestamps

    The frontend loads this once after processing completes, then uses it
    to draw the skeleton overlay and populate the coaching notes panel.
    """
    if video_id not in video_registry:
        raise HTTPException(status_code=404, detail="Video not found")

    info = video_registry[video_id]

    if info["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video is still {info['status']}. Wait for processing to complete."
        )

    analysis_path = info.get("analysis_path")
    if not analysis_path or not os.path.exists(analysis_path):
        raise HTTPException(status_code=404, detail="Analysis file not found")

    with open(analysis_path, "r") as f:
        analysis = json.load(f)

    return JSONResponse(analysis)


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
