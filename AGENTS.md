# Tennia — Tennis Biomechanics Analysis

> Guidance for Codex working in this repo. Read this first, then open the
> linked docs in `.Codex/docs/` only when a task touches that area.

## What this is (purpose)

Upload an iPhone tennis video → a computer-vision backend analyzes every frame
(player pose, joint angles, rule-based coaching notes) → a React dashboard plays
the original video back with a live skeleton overlay and an interactive 3D body
model. The long-term goal is a markerless, low-cost alternative to lab motion
capture (Qualisys/Vicon); see [roadmap](.Codex/docs/roadmap.md).

**Current honest status:** a working single-camera MVP. Pose + joint angles +
2D/3D overlay work end to end. Most of the "analytics" advertised in `README.md`
(ball tracking, court detection, shot classification, movement/heatmaps,
session metrics) exists as code but is **not wired into the running app** — see
[orphaned_code.md](.Codex/docs/orphaned_code.md). Trust the code over the older
root `.md` files.

## Tech stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI + Uvicorn (`backend/main.py`) |
| Pose (2D) | Ultralytics **YOLOv8n-pose** → 17 COCO keypoints, for the video overlay |
| Pose (3D) | Google **MediaPipe Pose** → 33 world landmarks (meters), for the 3D view |
| Video I/O | OpenCV (frame reads) + `ffmpeg` CLI (rotation fix / re-encode) |
| Analytics | NumPy joint-angle math + a rule-based coach (no ML/LLM, despite the `google-genai` dep) |
| Frontend | React 19 + TypeScript, Vite |
| 3D render | three.js via `@react-three/fiber` + `@react-three/drei` |
| Charts | Recharts |
| Transport | HTTP (upload / serve video / serve analysis JSON) + a progress-only WebSocket |

Both pose engines run **on CPU** on the current 2019 Intel Mac (no CUDA; MPS
needs Apple Silicon). This is the main performance constraint — see
[performance_and_hardware.md](.Codex/docs/performance_and_hardware.md).

## Key directories

```
backend/
  main.py                  FastAPI app + lifespan that loads models once (main.py:30)
  config.py                All tunables: model names, thresholds, court dims, COCO keypoints
  routers/
    video.py               Upload, ffmpeg rotation fix, serve video, serve analysis JSON
    websocket.py           Progress-only WebSocket (no frame streaming anymore)
  processing/
    analyzer.py            THE pipeline: reads frames → pose → angles → coach → writes JSON
  cv_pipeline/
    pose_3d.py             ACTIVE pose engine (YOLOv8 2D + MediaPipe 3D in one class)
    pose_estimator.py      ⚠ orphaned (separate YOLO-tracking class, unused)
    ball_tracker.py        ⚠ orphaned
    court_detector.py      ⚠ orphaned
  analytics/
    kinematics.py          ACTIVE — joint angles + angular velocity
    coach_llm.py           ACTIVE — rule-based coaching notes (misnamed; not an LLM)
    metrics.py / movement.py / shot_classifier.py / biomechanics.py   ⚠ orphaned
  utils/
    geometry.py            used only by orphaned analytics; drawing.py ⚠ orphaned
  uploads/                 saved videos + <id>_analysis.json (gitignored)

frontend/src/
  App.tsx                  top-level state machine (upload ↔ dashboard)
  hooks/useWebSocket.ts    progress WebSocket client
  components/
    VideoCanvas.tsx        HTML5 <video> + canvas skeleton overlay (interpolated)
    ThreeDWorld.tsx        three.js 3D skeleton from MediaPipe landmarks
    BiomechanicsCard / KinematicSequenceChart / AICoachPanel / UploadZone / Header   ACTIVE
    SpeedGauge / MiniCourt / ShotPlacementChart / MetricsGrid   ⚠ orphaned
  utils/types.ts           shared data shapes (FrameData, AnalysisData, CoachingNote)
  utils/constants.ts       API_BASE_URL / WS_BASE_URL (hardcoded localhost)
```

## Essential commands

**Backend** (needs `ffmpeg` on PATH — `brew install ffmpeg`):
```bash
cd backend
pip install -r requirements.txt        # first time
python main.py                         # serves http://localhost:8000 (reload on)
```

**Frontend:**
```bash
cd frontend
npm install                            # first time
npm run dev                            # http://localhost:5173
npm run build                          # tsc -b && vite build
npm run lint                           # eslint
```

**Tests:** there is no real test suite. `backend/test_upload.py` is a one-off
smoke script that POSTs a file to a running server. Use linters (`npm run lint`)
for code style — do not hand-format.

## When to open the deeper docs

| Open this | When you are… |
|-----------|---------------|
| [.Codex/docs/pipeline.md](.Codex/docs/pipeline.md) | Touching upload→process→playback flow, the dual pose engine, or frame timing |
| [.Codex/docs/data_contract.md](.Codex/docs/data_contract.md) | Changing the analysis JSON, keypoint names, or anything crossing backend↔frontend |
| [.Codex/docs/architectural_patterns.md](.Codex/docs/architectural_patterns.md) | Adding a module and want to match existing conventions |
| [.Codex/docs/orphaned_code.md](.Codex/docs/orphaned_code.md) | About to edit/delete a CV/analytics module, or asked "why isn't X working" |
| [.Codex/docs/performance_and_hardware.md](.Codex/docs/performance_and_hardware.md) | Anything about speed, CPU/GPU, model size, resolution, frame skipping |
| [.Codex/docs/roadmap.md](.Codex/docs/roadmap.md) | Discussing multi-camera, 3D triangulation, sensor fusion, or future direction |

> The root files `README.md`, `architecture_deep_dive.md`, `full_system_roadmap.md`,
> `swap_medipipe_to_yolo.md`, `walkthrough.md` are historical/aspirational. They
> contain useful vision and theory but are **out of date on implementation
> details** (e.g. they describe MediaPipe-only or YOLOv8m; reality is YOLOv8n +
> MediaPipe together). Verify against the code.
