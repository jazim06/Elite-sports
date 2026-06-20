# Data Contract (backend ↔ frontend)

The single coupling point between Python and React is the analysis JSON. Change
it on one side, change it on both. Producer and consumers below.

## Where it's defined

- **Produced:** `backend/processing/analyzer.py:185` (assembled) → written at `:203`
- **Serializers:** `_serialize_landmarks_2d` `analyzer.py:241`, `_serialize_landmarks_3d` `analyzer.py:258`
- **Served:** `GET /api/analysis/{id}` → `backend/routers/video.py:193`
- **Consumed:** typed in `frontend/src/utils/types.ts:73` (`AnalysisData`), loaded in `frontend/src/App.tsx:37`

## Shape

```jsonc
{
  "video_id": "9e22a0b0",
  "metadata": {
    "fps": 30.0,
    "total_frames": 275,
    "processed_frames": 138,      // may be < total_frames due to frame skipping
    "width": 1080, "height": 1920,
    "analysis_width": 480,        // resolution the models actually saw
    "analysis_height": 853,
    "duration_sec": 9.17,
    "processing_time_sec": 42.1
  },
  "frames": [
    {
      "frame": 2,                 // 1-based source frame index (not contiguous)
      "timestamp": 0.033,         // seconds = (frame-1)/fps, used to sync playback
      "landmarks_2d": {           // YOLO, NORMALIZED 0..1, for the video overlay
        "RIGHT_SHOULDER": { "x": 0.41, "y": 0.32, "v": 0.97 }  // v = confidence
      },
      "landmarks_3d": {           // MediaPipe world coords in METERS, for 3D view + angles
        "RIGHT_SHOULDER": { "x": 0.12, "y": -0.40, "z": -0.05, "v": 0.99 }
      },
      "joint_angles": {           // degrees; keys: knee_{left,right}, elbow_{left,right},
                                  //   shoulder_{left,right}, hip_{left,right}
        "elbow_right": 158.2
      },
      "angular_velocity": {       // deg/SEC (replaced deg/frame after summarize_biomechanics);
                                  // keys suffixed _vel; null on frames with no pose
        "elbow_right_vel": -42.3
      },
      "segment_velocity": {       // deg/sec; null on frames with no pose
        "pelvis": 120.4,          // rotation speed of hip line in transverse plane
        "trunk":  210.7,          // rotation speed of shoulder line in transverse plane
        "arm":    380.1,          // angular speed of upper-arm unit vector (SHOULDER→ELBOW)
        "hand":   610.3           // angular speed of forearm unit vector (ELBOW→WRIST)
      }
    }
  ],
  "coaching_notes": [             // deduped across the whole video, phase-aware
    {
      "timestamp": "0:01.5", "frame": 45, "joint": "elbow_right",
      "severity": "error",        // "error" | "warning" | "good"
      "flaw": "…", "actual_angle": 152.0, "optimal_range": [160, 180],
      "impact": "…", "drill": "…"
    }
  ],
  "kinematic_sequence": {
    "detected": true,
    "dominant_side": "RIGHT",
    "contact_frame": 83,
    "contact_time": 2.733,
    "phases": {
      "windup":        [2,  55],   // [start_frame, end_frame]
      "acceleration":  [55, 83],
      "contact":       83,
      "follow_through":[83, 105]
    },
    "peaks": {
      "pelvis": { "frame": 61, "time": 2.000, "speed_deg_per_sec": 142.3 },
      "trunk":  { "frame": 67, "time": 2.200, "speed_deg_per_sec": 230.5 },
      "arm":    { "frame": 74, "time": 2.433, "speed_deg_per_sec": 410.2 },
      "hand":   { "frame": 83, "time": 2.733, "speed_deg_per_sec": 650.8 }
    },
    "order": ["pelvis", "trunk", "arm", "hand"],
    "is_proximal_to_distal": true,
    "sequence_score": 87,          // 0–100; rewards correct order + magnitude summation + plausible timing gaps
    "hip_shoulder_separation": {
      "peak_deg": 34.7,            // degrees; trunk_angle − pelvis_angle (transverse plane)
      "peak_time": 2.100
    }
  }
}
```

## Conventions to preserve

- **Keypoint names are UPPERCASE** for both 2D and 3D (e.g. `RIGHT_SHOULDER`).
  See [architectural_patterns.md](architectural_patterns.md) §6.
- **`landmarks_2d` are normalized 0–1**; the frontend multiplies by the drawn
  video area (`VideoCanvas.tsx:193`). Never send pixels.
- **`landmarks_3d` are in meters** (MediaPipe world space); the 3D view negates
  y and z to make the figure stand upright (`ThreeDWorld.tsx:50`).
- **`v`** is confidence/visibility 0–1; consumers skip points below a threshold
  (kinematics `kinematics.py:88`, overlay `VideoCanvas.tsx:190`).
- **`frames` is sorted by timestamp and sparse** — frame indices are not
  contiguous when frame-skipping is on. Consumers must search/interpolate, not
  index by position (`VideoCanvas.tsx:75`).
- **`angular_velocity` is deg/sec** (not deg/frame) as of the kinematic-sequence
  refactor. Values are computed by `summarize_biomechanics()` via
  `np.gradient(smoothed_series, timestamps)` and written back to each frame.
- **`segment_velocity`** is set to `null` on frames where no pose was detected.
  Frontend must use `?.` or `?? 0` guards.
- **`kinematic_sequence.sequence_score`** is a heuristic 0–100 score. It is
  coaching-derived, not lab-validated. See `config.py:BIOMECH_THRESHOLDS` for
  threshold documentation.

## Known drift in `types.ts`

`frontend/src/utils/types.ts` carries several interfaces (`BallData`,
`ShotData`, `SessionMetrics`, `PlayerData.court_position`, the rich
`ProgressPayload.all_notes`, etc.) that the backend **does not produce** — they
belong to the orphaned features (see [orphaned_code.md](orphaned_code.md)).
`CoachingNote` (`types.ts:88`) is the shape that actually matches the backend;
the WebSocket in practice only sends `{type, progress, current_frame,
total_frames, status}` (`websocket.py:60`).
