"""
Video Analyzer — Background processor for the two-pass architecture.

HOW IT WORKS (for beginners):
─────────────────────────────
This module processes an entire video from start to finish in the background.
Instead of sending each frame to the browser one-by-one (the old way), it:

1. Opens the video file with OpenCV
2. Reads EVERY frame, one at a time
3. For each frame, runs MediaPipe to find the person's body pose (33 landmarks)
4. Calculates joint angles from those landmarks (knee bend, elbow angle, etc.)
5. Checks if any angles are outside the "good" range → generates coaching notes
6. Saves ALL of this data into a single .json file

The frontend then loads this .json file and uses it to draw the skeleton
on top of the native HTML5 video player. No more streaming images!

WHY THIS IS BETTER:
- The video plays at full native framerate (smooth, not a slideshow)
- The skeleton is drawn by the browser (super fast)
- You can scrub, pause, slow-mo — all handled by the browser's video player
- The backend doesn't have to stay connected during playback
"""

import cv2
import json
import os
import sys
import time
import traceback
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add backend directory to path to fix ModuleNotFoundError during uvicorn multiprocessing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import UPLOAD_DIR
from cv_pipeline.pose_3d import Pose3DEstimator
from analytics.kinematics import KinematicsEngine, summarize_biomechanics
from analytics.coach_llm import AICoach

# Thread pool for running CPU-heavy processing without blocking the async server
_executor = ThreadPoolExecutor(max_workers=2)

# Global model instances (loaded once, shared across all analyses)
_pose_3d: Pose3DEstimator = None
_ai_coach: AICoach = None


def init_models():
    """Load ML models. Called once on server startup."""
    global _pose_3d, _ai_coach
    print("⏳ Loading YOLOv8-Pose model...")
    _pose_3d = Pose3DEstimator()
    _ai_coach = AICoach()
    print("✅ Biomechanics engine ready!")


def _process_video_sync(video_path: str, video_info: dict) -> dict:
    """
    Process the entire video synchronously (runs in a thread).

    This is the CORE function. It reads every frame, runs pose estimation,
    calculates angles, and builds the full analysis result.

    Args:
        video_path: Path to the .mp4 file on disk
        video_info: Mutable dict from video_registry (we update progress here)

    Returns:
        dict with all analysis data (saved as JSON later)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    # ── Video properties ──────────────────────────────────
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Track the actual resolution the pose model will see (after resize)
    max_process_width = 480  # 480px provides a massive speedup and is plenty for YOLOv8n and MediaPipe
    analysis_width = min(width, max_process_width)
    analysis_height = int(height * (analysis_width / width)) if width > max_process_width else height

    video_info["total_frames"] = total_frames
    video_info["status"] = "processing"

    # ── Per-video analytics state ─────────────────────────
    kinematics = KinematicsEngine()
    frames_data = []       # Per-frame analysis results

    frame_num = 0
    # Process every Nth frame. If it's a 60fps video, skip every other frame (30fps) to double processing speed.
    # The frontend interpolation logic handles the gaps perfectly.
    process_every_n = 2 if fps > 45 else 1
    processed_count = 0

    print(f"🎬 Processing video: {total_frames} frames @ {fps:.1f} fps")
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_num += 1

            # Skip frames for performance
            if frame_num % process_every_n != 0:
                continue

            processed_count += 1

            # Get the exact linear timestamp for this frame.
            # We use (frame_num - 1) / fps because CAP_PROP_POS_MSEC can be unreliable on some OS/backends
            # and may drift ahead of the video. The browser plays constant frame rate video strictly linearly.
            timestamp_sec = (frame_num - 1) / fps

            # Resize for faster processing
            frame = _resize_frame(frame, max_width=max_process_width)

            # ── Run YOLOv8-Pose ────────────────────────
            pose_result = _pose_3d.process_frame(frame)

            # Build per-frame data
            frame_entry = {
                "frame": frame_num,
                "timestamp": round(timestamp_sec, 3),
                "landmarks_2d": None,
                "joint_angles": None,
                "angular_velocity": None,
            }

            if pose_result:
                landmarks_3d = pose_result["landmarks_3d"]
                landmarks_2d = pose_result["landmarks_2d"]

                # Calculate joint angles
                kinematics_data = kinematics.analyze_pose(landmarks_3d)

                frame_entry["landmarks_2d"] = _serialize_landmarks_2d(landmarks_2d)
                frame_entry["landmarks_3d"] = _serialize_landmarks_3d(landmarks_3d)
                frame_entry["joint_angles"] = kinematics_data.get("angles", {})
                frame_entry["angular_velocity"] = kinematics_data.get("angular_velocities", {})

            frames_data.append(frame_entry)

            # Update progress for the frontend to poll
            progress = round(frame_num / max(total_frames, 1) * 100, 1)
            video_info["current_frame"] = frame_num
            video_info["progress"] = progress

    except Exception as e:
        print(f"❌ Error processing video: {e}")
        traceback.print_exc()
        video_info["status"] = "error"
        raise
    finally:
        cap.release()

    elapsed = time.time() - start_time
    print(f"✅ Processing complete: {processed_count} frames in {elapsed:.1f}s "
          f"({processed_count/elapsed:.1f} fps)")

    # ── Two-pass: smooth, compute segment velocities, score kinematic sequence ──
    print("📐 Running biomechanics summarizer...")
    kinematic_sequence = summarize_biomechanics(frames_data, fps)

    # ── Phase-aware coaching (uses contact frame + sequence order) ──────────
    coaching_notes = _ai_coach.analyze(frames_data, kinematic_sequence, fps)
    print(f"💬 Generated {len(coaching_notes)} coaching note(s)")

    # ── Build the final analysis result ───────────────────
    analysis = {
        "video_id": video_info["id"],
        "metadata": {
            "fps": fps,
            "total_frames": total_frames,
            "processed_frames": processed_count,
            "width": width,
            "height": height,
            "analysis_width": analysis_width,
            "analysis_height": analysis_height,
            "duration_sec": round(total_frames / fps, 2),
            "processing_time_sec": round(elapsed, 2),
        },
        "frames": frames_data,
        "coaching_notes": coaching_notes,
        "kinematic_sequence": kinematic_sequence,
    }

    # Save to JSON file alongside the video
    json_path = os.path.splitext(video_path)[0] + "_analysis.json"
    with open(json_path, "w") as f:
        json.dump(analysis, f)

    video_info["status"] = "completed"
    video_info["progress"] = 100
    video_info["analysis_path"] = json_path

    print(f"💾 Analysis saved: {json_path} ({os.path.getsize(json_path) / 1024:.0f} KB)")
    return analysis


async def process_video_async(video_path: str, video_info: dict) -> dict:
    """
    Run the heavy video processing in a background thread so it doesn't
    block the FastAPI async event loop.

    This is called from the upload endpoint. The frontend polls for progress
    via the /api/status/{video_id} endpoint.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _process_video_sync,
        video_path,
        video_info,
    )


def _resize_frame(frame: np.ndarray, max_width: int = 720) -> np.ndarray:
    """Resize frame if wider than max_width."""
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / w
        return cv2.resize(frame, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
    return frame


def _serialize_landmarks_2d(landmarks_2d: dict) -> dict:
    """
    Serialize normalized landmark coordinates for JSON output.

    Coordinates are kept as normalized floats (0.0–1.0) so the frontend
    can map them to any canvas size without knowing the backend resolution.
    Visibility is included so the frontend can skip low-confidence points.
    """
    result = {}
    for name, coords in landmarks_2d.items():
        result[name] = {
            "x": round(coords["x"], 5),
            "y": round(coords["y"], 5),
            "v": round(coords.get("visibility", 1.0), 3),
        }
    return result

def _serialize_landmarks_3d(landmarks_3d: dict) -> dict:
    """
    Serialize 3D landmarks for JSON output.
    """
    result = {}
    for name, coords in landmarks_3d.items():
        result[name] = {
            "x": round(coords["x"], 5),
            "y": round(coords["y"], 5),
            "z": round(coords["z"], 5),
            "v": round(coords.get("visibility", 1.0), 3),
        }
    return result
