"""
WebSocket Router — Biomechanics-focused processing pipeline.

Performance optimizations:
- Process every 2nd frame (skip 1) to halve MediaPipe load
- Reduced frame size to 720px max width
- JPEG quality at 60 for smaller payloads
- AI notes are accumulated and sent as a growing list

Focus: MediaPipe 3D Pose → Kinematics → Rule-Based AI Coaching Notes.
"""
import cv2
import base64
import asyncio
import traceback
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from config import MAX_FRAME_WIDTH
from cv_pipeline.pose_3d import Pose3DEstimator
from analytics.kinematics import KinematicsEngine
from analytics.coach_llm import AICoach
from routers.video import video_registry

router = APIRouter(tags=["websocket"])

# ── Performance Tuning ─────────────────────────────────
PROCESS_EVERY_N = 2       # Only run MediaPipe on every Nth frame
WS_JPEG_QUALITY = 60      # Lower JPEG quality = smaller payloads
WS_MAX_WIDTH = 720        # Smaller frames = faster encode/decode
AI_CHECK_INTERVAL = 15    # Check for flaws every N processed frames

# Shared model instances
pose_3d: Optional[Pose3DEstimator] = None
ai_coach: Optional[AICoach] = None


def init_models():
    """Initialize CV models. Called once on app startup."""
    global pose_3d, ai_coach
    print("⏳ Loading MediaPipe 3D Pose model...")
    pose_3d = Pose3DEstimator()
    ai_coach = AICoach()
    print("✅ Biomechanics engine ready!")


@router.websocket("/ws/analytics/{video_id}")
async def analytics_stream(websocket: WebSocket, video_id: str):
    """
    WebSocket endpoint — processes video and streams:
    - Annotated frames (base64 JPEG, every Nth frame)
    - 3D joint angles
    - Accumulated AI coaching notes (timestamped, scrollable)
    """
    await websocket.accept()

    if video_id not in video_registry:
        await websocket.send_json({"error": "Video not found"})
        await websocket.close()
        return

    video_info = video_registry[video_id]
    video_path = video_info["path"]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        await websocket.send_json({"error": "Failed to open video file"})
        await websocket.close()
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_info["status"] = "processing"
    video_info["total_frames"] = total_frames

    await websocket.send_json({
        "type": "metadata",
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
    })

    # Per-video state
    kinematics = KinematicsEngine()
    coaching_notes = []    # Accumulated timestamped notes
    seen_flaws = set()     # Deduplicate: (joint, severity) combos
    frame_num = 0
    processed_count = 0
    playback_speed = 1.0
    is_paused = False

    try:
        while True:
            # Check for client messages
            msg_received = False
            msg = {}
            try:
                # If paused, wait longer (0.1s) to avoid spinning CPU. Otherwise poll quickly (0.001s).
                msg = await asyncio.wait_for(
                    websocket.receive_json(), timeout=0.1 if is_paused else 0.001
                )
                msg_received = True
            except asyncio.TimeoutError:
                pass

            if msg_received:
                action = msg.get("action")
                if action == "pause":
                    is_paused = True
                elif action == "play":
                    is_paused = False
                elif action == "speed":
                    playback_speed = msg.get("value", 1.0)
                elif action == "seek":
                    seek_frame = msg.get("frame", 0)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
                    frame_num = seek_frame
                    video_info["status"] = "processing"
            
            # If paused AND we didn't just receive a 'seek' command, don't read the next frame.
            if is_paused and not (msg_received and msg.get("action") == "seek"):
                continue

            ret, frame = cap.read()
            if not ret:
                # End of video reached
                if video_info["status"] != "completed":
                    video_info["status"] = "completed"
                    video_info["progress"] = 100
                    await websocket.send_json({
                        "type": "complete",
                        "all_notes": coaching_notes,
                    })
                # Don't break the connection! Wait for user commands (like seek)
                await asyncio.sleep(0.05)
                continue

            frame_num += 1

            # Skip frames for performance
            if frame_num % PROCESS_EVERY_N != 0:
                continue

            processed_count += 1
            frame = _resize_frame(frame, WS_MAX_WIDTH)

            # ── 3D Pose Estimation ──────────────────────
            pose_result = pose_3d.process_frame(frame)

            player_data = None
            kinematics_data = {}
            new_notes = []

            if pose_result:
                annotated = pose_result["annotated_frame"]
                kinematics_data = kinematics.analyze_pose(pose_result["landmarks_3d"])

                player_data = {
                    "joint_angles_3d": kinematics_data.get("angles", {}),
                    "angular_velocity": kinematics_data.get("angular_velocities", {}),
                }

                # AI analysis at intervals
                if processed_count % AI_CHECK_INTERVAL == 0 and kinematics_data.get("angles"):
                    frame_notes = ai_coach.analyze_frame(frame_num, fps, kinematics_data)

                    for note in frame_notes:
                        # Deduplicate: only add a note if we haven't flagged this exact flaw before
                        flaw_key = (note["joint"], note["flaw"])
                        if flaw_key not in seen_flaws:
                            seen_flaws.add(flaw_key)
                            coaching_notes.append(note)
                            new_notes.append(note)
            else:
                annotated = frame

            # ── Encode and send ──────────────────────────
            _, buffer = cv2.imencode(
                ".jpg", annotated,
                [cv2.IMWRITE_JPEG_QUALITY, WS_JPEG_QUALITY]
            )
            frame_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

            payload = {
                "type": "frame",
                "frame_number": frame_num,
                "total_frames": total_frames,
                "frame_data": frame_b64,
                "player": player_data,
                "new_notes": new_notes,          # Only NEW notes this frame
                "total_notes": len(coaching_notes),
            }

            await websocket.send_json(payload)

            video_info["current_frame"] = frame_num
            video_info["progress"] = round(frame_num / max(total_frames, 1) * 100, 1)

            delay = (1.0 / fps) * PROCESS_EVERY_N / playback_speed
            await asyncio.sleep(max(delay - 0.01, 0.005))

    except WebSocketDisconnect:
        print(f"Client disconnected from video {video_id}")
    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        cap.release()
        video_info["status"] = "completed"
        video_info["progress"] = 100

        try:
            await websocket.send_json({
                "type": "complete",
                "all_notes": coaching_notes,  # Send ALL notes at completion
            })
        except Exception:
            pass


def _resize_frame(frame: np.ndarray, max_width: int = 720) -> np.ndarray:
    """Resize frame for processing efficiency."""
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_w = max_width
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return frame
