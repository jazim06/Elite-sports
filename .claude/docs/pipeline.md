# The Pipeline (end to end)

How a video becomes an analyzed, playable dashboard. This is the **actually
running** path — ignore the frame-streaming description in the older root docs.

## Flow

```
iPhone .mov/.mp4
   │  POST /api/upload                         backend/routers/video.py:87
   ▼
save to backend/uploads/<id>.<ext>            video.py:111
   │
   ▼ ffmpeg re-encode → H.264, bake rotation, strip audio, +faststart
fix_rotation() → <id>_fixed.mp4               video.py:32
   │  register in video_registry, status=processing
   ▼  asyncio.create_task(process_video_async)  video.py:133
   │
   ▼  (runs in ThreadPoolExecutor)
_process_video_sync                           backend/processing/analyzer.py:61
   │   OpenCV reads frames; resize to ≤480px wide   analyzer.py:86,129
   │   skip every 2nd frame if source >45fps        analyzer.py:102
   │   per frame:
   │     Pose3DEstimator.process_frame            cv_pipeline/pose_3d.py:89
   │        ├─ YOLOv8n-pose → 17 COCO 2D keypoints (normalized)  pose_3d.py:127
   │        └─ MediaPipe Pose → 33 world landmarks (meters)      pose_3d.py:156
   │     KinematicsEngine.analyze_pose(3d) → joint angles + vel  analytics/kinematics.py:72
   │     every 15 processed frames: AICoach.analyze_frame        analytics/coach_llm.py:28
   │   update video_info["progress"]                analyzer.py:168
   ▼
write <id>_fixed_analysis.json, status=completed  analyzer.py:203
   │
   ▼  meanwhile the browser was polling:
WebSocket /ws/progress/<id>  (progress % only)   backend/routers/websocket.py:25
   │  on "complete" →
GET /api/analysis/<id>  → full JSON               video.py:193 → App.tsx:37
GET /api/video/<id>     → the .mp4                 video.py:166
   ▼
VideoCanvas: native <video> + canvas skeleton    frontend/src/components/VideoCanvas.tsx
ThreeDWorld: three.js skeleton from landmarks_3d frontend/src/components/ThreeDWorld.tsx
```

## The dual pose engine (important)

`Pose3DEstimator` (despite the name, it's the *whole* pose stage) runs **two
models on every frame** — `backend/cv_pipeline/pose_3d.py:52`:

| Engine | Output | Used for | Coordinates |
|--------|--------|----------|-------------|
| YOLOv8n-pose | 17 COCO keypoints | the 2D video overlay | normalized 0–1, key `landmarks_2d` |
| MediaPipe Pose | 33 world landmarks | joint angles **and** the 3D view | meters, key `landmarks_3d` |

- Joint angles are computed from the **MediaPipe 3D** landmarks, not YOLO:
  `analyzer.py:148` passes `landmarks_3d` into the kinematics engine.
- The 2D overlay uses **YOLO** points (more accurate pixel localization).
- If MediaPipe fails on a frame, it falls back to YOLO points flattened to
  `z=0`: `pose_3d.py:175`.

This is why both `mediapipe` and `ultralytics` are required. Running only one
engine would break either the 3D view or the overlay/angles.

### Model selection caveat
`config.py:13` defines `POSE_MODEL = "yolov8n-pose.pt"`, but
`Pose3DEstimator.__init__` **hardcodes its own default** `"yolov8n-pose.pt"`
(`pose_3d.py:63`) and `init_models()` constructs it with no argument — so
`config.POSE_MODEL` is not actually consulted by the active path. The
`yolov8m-pose.pt` file in `backend/` is **not used by default**, even though
several comments/docstrings claim YOLOv8m. To change the model, edit
`pose_3d.py:63` (and wiring it to read from config would be a small cleanup).

## Timing / frame-rate notes

- Processing resolution is capped at **480px** wide (`analyzer.py:86`) — a big
  speed lever; quality vs. speed tradeoff lives here.
- Frame skipping: only sources >45fps drop every 2nd frame (`analyzer.py:102`).
- Timestamps are `(frame_num-1)/fps` (`analyzer.py:126`), deliberately linear so
  they line up with the browser's constant-rate playback; the frontend
  interpolates between analyzed frames (`VideoCanvas.tsx:75`,`:148`).
- AI coaching runs every 15 processed frames (`analyzer.py:104`), not every frame.

## The coach is rule-based, not an LLM

`AICoach` (`backend/analytics/coach_llm.py:6`) is a small dictionary of optimal
joint-angle ranges with canned flaw text and drills (`:9`). There is **no
Gemini/LLM call** anywhere in the active code, even though `google-genai` is in
`requirements.txt` and root docs mention `GEMINI_API_KEY`. It currently only has
rules for `knee_right` and `elbow_right`. Extending the coach = adding entries to
the `rules` dict.
