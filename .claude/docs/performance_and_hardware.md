# Performance & Hardware

## Current machine reality

Development is on a **2019 Intel MacBook Pro (i7, no NVIDIA GPU)**. Consequences:

- **No CUDA** (Intel, not NVIDIA).
- **No MPS** either — Apple's Metal/MPS PyTorch backend requires *Apple Silicon*;
  it is unavailable on Intel Macs. So Ultralytics' auto device-select
  (`pose_3d.py:101`, no `device=` passed) resolves to **CPU**.
- **MediaPipe runs CPU-only** on macOS regardless (TensorFlow Lite + XNNPACK).

Net: **the entire pose stage runs on CPU**, and it runs *two* models per frame
(YOLOv8n-pose + MediaPipe). This is the dominant cost and the reason processing a
short clip takes tens of seconds. The two-pass design hides this from playback —
analysis happens once up front, then playback is smooth and native.

> A GPU (NVIDIA/CUDA, or an Apple-Silicon Mac for MPS) is the planned upgrade.
> It mainly speeds up **pass-1 processing time**; it does not change the
> architecture. See [roadmap.md](roadmap.md) for the eventual Jetson + TensorRT
> direction.

## Speed levers (in the active path)

Tune these in `backend/` before reaching for hardware:

| Lever | Location | Effect |
|-------|----------|--------|
| Processing resolution (480px) | `processing/analyzer.py:86` | Biggest CPU lever. Lower = faster, less accurate keypoints. |
| Frame skip threshold | `processing/analyzer.py:102` | Currently only >45fps sources skip every 2nd frame. Skipping more = faster, relies on frontend interpolation. |
| Pose model size | `cv_pipeline/pose_3d.py:63` | `yolov8n` (current) → `s`/`m`/`l` trades speed for accuracy. |
| Run one engine, not two | `cv_pipeline/pose_3d.py:80`,`:156` | MediaPipe (3D) roughly doubles per-frame cost. Dropping it loses the 3D view + breaks angle calc (angles use MediaPipe 3D — see [pipeline.md](pipeline.md)). |
| MediaPipe complexity | `cv_pipeline/pose_3d.py:82` (`model_complexity=0`) | Already at the fastest setting. |
| AI-check interval (15) | `processing/analyzer.py:104` | Minor; coach is cheap. |

## Things that are *not* the bottleneck

- The coach and kinematics are pure NumPy/Python and negligible.
- The WebSocket only sends progress %, and the video is served as a normal file
  — neither is a perf concern (unlike the old streaming design the root docs
  describe).
- `ffmpeg` re-encode on upload (`routers/video.py:32`) costs a few seconds once
  per video; it also enables in-browser seeking (`+faststart`).

## If/when a GPU is available

- For NVIDIA: install a CUDA-enabled PyTorch; Ultralytics will pick `cuda`
  automatically. MediaPipe stays CPU — consider replacing MediaPipe-3D with a
  GPU 3D-lift, or dropping to YOLO-only 2D, depending on goals.
- For Apple Silicon: YOLO will use `mps` automatically; MediaPipe stays CPU.
- The device-resolution helper already exists for the tracker classes
  (`_resolve_device()` at `pose_estimator.py:100`); the active `pose_3d.py` would
  just need a `device=` argument threaded through if explicit control is wanted.
