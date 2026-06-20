# Architectural Patterns & Conventions

Patterns that recur across the codebase. Follow these when adding code so new
work matches what's already here. Each is backed by ≥2 call sites.

---

## 1. Two-pass "process then play back" architecture

The defining design decision. The backend **never streams frames** to the
browser. It analyzes the whole video once, writes a JSON sidecar, and the
frontend then plays the *original* video natively with overlays synced to time.

- Upload kicks off background processing: `backend/routers/video.py:133`
- Whole-video processing loop: `backend/processing/analyzer.py:61`
- Result written as `<video>_analysis.json`: `backend/processing/analyzer.py:203`
- Frontend fetches that JSON once, then sets the video URL: `frontend/src/App.tsx:37`
- Playback + overlay (not streaming): `frontend/src/components/VideoCanvas.tsx:104`
- The WebSocket only carries progress %, never pixels: `backend/routers/websocket.py:25`

**Why:** smooth native playback (scrub/pause/slow-mo handled by the browser),
backend can disconnect after processing. When adding a feature, produce data
into the JSON during pass 1 and render it during pass 2 — don't add a live
stream.

---

## 2. Models loaded once as module-level singletons

Heavy models are instantiated a single time at server startup and shared across
all requests via module globals — never per-request.

- Globals + `init_models()`: `backend/processing/analyzer.py:47` and `:52`
- Invoked from the FastAPI lifespan on startup: `backend/main.py:30`
- Inside the pose class, both YOLO and MediaPipe load once in `__init__`:
  `backend/cv_pipeline/pose_3d.py:75` and `:80`

**When adding a model/heavy resource:** add it to `init_models()`, hold it in a
module global, reuse it.

---

## 3. Background-thread offload to keep the async loop free

CPU-bound CV work runs in a `ThreadPoolExecutor`, fired from the async upload
handler so the event loop (and the progress endpoints) stay responsive.

- Executor + `run_in_executor`: `backend/processing/analyzer.py:45` and `:215`
- Fire-and-forget task from the route: `backend/routers/video.py:133`

---

## 4. Shared mutable `video_info` dict as the progress channel

Processing state is a plain dict held in the in-memory `video_registry`. The
worker is handed the same dict **by reference** and mutates `progress` /
`status` / `current_frame` in place; the status endpoint and the WebSocket just
read it. No DB, no queue.

- Registry + per-video dict: `backend/routers/video.py:29` and `:121`
- Worker mutates it as it goes: `backend/processing/analyzer.py:168`
- Readers: `backend/routers/video.py:145` (poll) and `backend/routers/websocket.py:49`

**Caveat:** state is process-memory only — restarting the backend forgets all
uploads. Fine for the MVP; revisit if multi-worker/persistence is needed.

---

## 5. Normalized (0.0–1.0) coordinate contract

2D keypoints cross the wire as fractions of frame width/height, never pixels, so
the frontend can map onto any canvas size without knowing backend resolution.

- Backend normalizes on extraction: `backend/cv_pipeline/pose_3d.py:145`
- Serialized as-is to JSON: `backend/processing/analyzer.py:241`
- Frontend maps fraction → draw area: `frontend/src/components/VideoCanvas.tsx:193`

Keep this invariant. See [data_contract.md](data_contract.md) for the full shape.

---

## 6. UPPERCASE keypoint names as the cross-engine lingua franca

YOLO (COCO, lowercase) and MediaPipe (already uppercase) outputs are both keyed
by UPPERCASE names (`RIGHT_SHOULDER`, …) so the kinematics engine and the
frontend treat the two engines interchangeably.

- COCO→uppercase map: `backend/cv_pipeline/pose_3d.py:49`, applied at `:137`
- MediaPipe names are uppercase natively: `backend/cv_pipeline/pose_3d.py:165`
- Angle definitions assume uppercase: `backend/analytics/kinematics.py:25`
- Frontend skeleton connections use uppercase: `frontend/src/components/VideoCanvas.tsx:21`, `ThreeDWorld.tsx:8`

Note YOLO emits **17** keypoints, MediaPipe **33** — the 3D view uses extra
MediaPipe joints (feet/heels) the 2D view doesn't have.

---

## 7. Graceful degradation / fallback chains

CV steps assume detection can fail and always have a fallback rather than
throwing. This is pervasive across the pipeline.

- MediaPipe 3D missing → reuse YOLO points with `z=0`: `backend/cv_pipeline/pose_3d.py:175`
- `ffmpeg` not installed / fails / times out → use the original file: `backend/routers/video.py:51`, `:71`, `:79`
- (orphaned, same pattern) ball detect YOLO → HSV fallback: `backend/cv_pipeline/ball_tracker.py:130`
- (orphaned) court detect returns `False` instead of raising on any failed stage: `backend/cv_pipeline/court_detector.py:52`

When adding a detector, return `None`/`False`/a degraded value rather than
raising into the frame loop.

---

## 8. Stateful "engine" classes with config-driven thresholds

Per-concern classes share a shape: `__init__` sets up state + thresholds,
a per-frame method returns a dict, stateful trackers expose `reset()`. Magic
numbers live in `backend/config.py`, not inline.

- `KinematicsEngine` (history deques, joint table): `backend/analytics/kinematics.py:5`
- `AICoach` (rules dict of optimal ranges + drills): `backend/analytics/coach_llm.py:6`
- Thresholds centralized: `backend/config.py:16`–`:47`
- The `__init__` / `process_frame(...) -> dict` / `reset()` lifecycle recurs in
  the CV trackers (`pose_estimator.py:118`, `ball_tracker.py:230`,
  `court_detector.py:145`) — match it for any new tracker.

---

## 9. Deduplicate-with-a-`seen`-set

Repeated events are collapsed via a set of keys so the same finding isn't
emitted every frame.

- Coaching notes deduped by `(joint, flaw)`: `backend/processing/analyzer.py:160`
- (orphaned) shot debounce via frame counter: `backend/analytics/shot_classifier.py:28`

---

## 10. Frontend interpolation decouples processing fps from playback fps

Because pass 1 may skip frames, the overlay binary-searches the two analyzed
frames bounding the current video time and linearly interpolates landmarks — so
the skeleton stays smooth at native playback fps.

- Bounding-frame binary search: `frontend/src/components/VideoCanvas.tsx:75`
- Lerp between the two frames: `frontend/src/components/VideoCanvas.tsx:148`
- Render loop driven by `requestAnimationFrame`: `frontend/src/components/VideoCanvas.tsx:241`

Corollary: timestamps are derived linearly as `(frame-1)/fps`, deliberately not
from OpenCV's `CAP_PROP_POS_MSEC` (`backend/processing/analyzer.py:126`), so the
backend's frame clock matches the browser's constant-rate playback clock.

---

## 11. Device auto-resolution (cuda → mps → cpu)

Where device is chosen explicitly, it's resolved best-available with a safe CPU
fallback. The active pose path currently relies on Ultralytics' own auto-select
(no device passed at `pose_3d.py:101`); the helper exists in the tracker classes.

- `_resolve_device()`: `backend/cv_pipeline/pose_estimator.py:100`, `ball_tracker.py:236`

On the current Intel Mac all of these resolve to CPU.
