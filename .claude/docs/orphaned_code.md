# Orphaned / Unused Code

These modules exist and look complete, but **nothing imports them** in the
running app. They are scaffolding from the original frame-by-frame streaming
design that `README.md` and `architecture_deep_dive.md` still describe. The
migration to the two-pass + YOLO pipeline left them behind.

**Before editing or deleting any file here, confirm it's still unused** (the
import graph below was true as of this writing — re-verify with grep).

## How to verify what's live

The active backend import chain is small:

```
main.py → processing.analyzer
            → cv_pipeline.pose_3d.Pose3DEstimator
            → analytics.kinematics.KinematicsEngine
            → analytics.coach_llm.AICoach
routers.video → processing.analyzer.process_video_async
routers.websocket → routers.video.video_registry
```

Quick check for any module:
```bash
cd backend
grep -rln "import.*<module>\|from.*<module>" --include='*.py' . \
  | grep -v venv | grep -v __pycache__
```

## Orphaned backend modules

| File | What it is | Status |
|------|-----------|--------|
| `backend/cv_pipeline/pose_estimator.py` | A *second* pose class (`PoseEstimator`) using YOLO `.track()` with BoTSORT IDs. **Not** the one in use — the active class is `pose_3d.py`'s `Pose3DEstimator`. | unused |
| `backend/cv_pipeline/ball_tracker.py` | `BallTracker` + `KalmanBallFilter`: YOLO ball detect + HSV fallback + Kalman smoothing. | unused |
| `backend/cv_pipeline/court_detector.py` | `CourtDetector`: white-line extraction → Hough → homography to court meters. | unused |
| `backend/analytics/movement.py` | `MovementAnalyzer`: speed/accel/distance/heatmap/zones. | unused |
| `backend/analytics/shot_classifier.py` | `ShotClassifier`: rule-based forehand/backhand/serve/volley. | unused |
| `backend/analytics/metrics.py` | `SessionMetrics` aggregation. | unused |
| `backend/analytics/biomechanics.py` | An alternate angle/symmetry engine (overlaps with `kinematics.py`). | unused |
| `backend/utils/drawing.py` | OpenCV skeleton/overlay drawing — irrelevant now that the **frontend** draws overlays. | unused |
| `backend/utils/geometry.py` | Vector/court math. Imported **only** by the orphaned analytics above, so transitively dead in the running app. | indirectly unused |

## Orphaned frontend components

Defined but not imported by `App.tsx` (verify: `grep -rl <Name> frontend/src`):

| File | Status |
|------|--------|
| `frontend/src/components/SpeedGauge.tsx` | unused |
| `frontend/src/components/MiniCourt.tsx` | unused |
| `frontend/src/components/ShotPlacementChart.tsx` | unused |
| `frontend/src/components/MetricsGrid.tsx` | unused |

Several `types.ts` interfaces (`BallData`, `ShotData`, `SessionMetrics`, parts of
`PlayerData`) exist only to support these — see [data_contract.md](data_contract.md).

## Stray model weights

`backend/yolov8m-pose.pt` and `backend/yolov8n.pt` sit in the repo but the active
path loads only `yolov8n-pose.pt` (`pose_3d.py:63`). `yolov8n.pt` (plain
detection) would be needed by the ball tracker if it were ever wired up.
(All `*.pt` are gitignored.)

## What this means for tasks

- These files are a **feature backlog, not bugs** — the building blocks for ball
  tracking, court mapping, shot stats, and movement heatmaps already exist and
  mostly just need wiring into `analyzer.py` (pass 1) + a frontend panel (pass 2)
  + fields in the analysis JSON.
- If asked "why doesn't ball tracking / the mini-court / shot counts work?" the
  answer is: the code exists but is **not connected** to the running pipeline.
- Don't trust the `README.md` "Analytics Engine" / "Ball Tracker" / "Court
  Detector" bullets as descriptions of current behavior.
