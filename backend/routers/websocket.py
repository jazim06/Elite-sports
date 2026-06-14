"""
WebSocket Router — Progress updates only.

IN THE OLD SYSTEM:
    The WebSocket streamed every frame as a base64 JPEG image. This was slow
    because each frame was ~50KB of text, and the browser had to decode it.

IN THE NEW TWO-PASS SYSTEM:
    The WebSocket is MUCH simpler. It only sends small progress updates
    (a few bytes each) so the frontend can show a progress bar.
    Once processing is done, the frontend fetches the analysis data via
    a normal HTTP GET request instead.

    The WebSocket is optional — the frontend could also just poll
    /api/status/{video_id} — but WebSocket gives instant updates.
"""
import asyncio
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from routers.video import video_registry

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/progress/{video_id}")
async def progress_stream(websocket: WebSocket, video_id: str):
    """
    WebSocket that sends processing progress updates.

    Message format:
    {
        "type": "progress",
        "progress": 45.2,          // percentage (0-100)
        "current_frame": 124,
        "total_frames": 275,
        "status": "processing"     // "processing" | "completed" | "error"
    }
    """
    await websocket.accept()

    if video_id not in video_registry:
        await websocket.send_json({"type": "error", "error": "Video not found"})
        await websocket.close()
        return

    try:
        last_progress = -1

        while True:
            info = video_registry.get(video_id)
            if not info:
                break

            current_progress = info["progress"]
            status = info["status"]

            # Only send if progress changed (avoid spamming)
            if current_progress != last_progress:
                last_progress = current_progress
                await websocket.send_json({
                    "type": "progress",
                    "progress": current_progress,
                    "current_frame": info["current_frame"],
                    "total_frames": info["total_frames"],
                    "status": status,
                })

            # If processing is done, send final message and close
            if status in ("completed", "error"):
                await websocket.send_json({
                    "type": "complete" if status == "completed" else "error",
                    "status": status,
                    "progress": 100 if status == "completed" else current_progress,
                })
                break

            # Poll interval — 200ms gives smooth progress bar updates
            await asyncio.sleep(0.2)

    except WebSocketDisconnect:
        print(f"Progress client disconnected for video {video_id}")
    except Exception as e:
        print(f"Progress WebSocket error: {e}")
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
