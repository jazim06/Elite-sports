# Vision & Roadmap

Condensed pointer to the long-form vision docs in the repo root. Read those for
depth; this summarizes intent and flags what's real vs. aspirational.

## The big picture

Tennia aims to grow from a **single-iPhone markerless MVP** into a multi-camera,
sub-centimeter biomechanics system — a low-cost alternative to lab motion capture
(Qualisys/Vicon) for tennis coaching. The bet: markerless AI trades lab-grade
accuracy for radical convenience and cost.

## Where to read more (root files — vision, not current state)

| File | Contents | Trust level |
|------|----------|-------------|
| `architecture_deep_dive.md` | How the system works, accuracy vs. Qualisys, what real-time would take, the two-pass argument. | Concepts ✅ / implementation details ❌ (says MediaPipe-only; reality is YOLO+MediaPipe). The two-pass design it recommends **is now implemented**. |
| `full_system_roadmap.md` | The full vision: 8-camera sync, calibration + DLT triangulation, Jetson Orin edge compute, EMG/IMU/insole sensor fusion, accuracy targets, phase plan. | Aspirational/forward-looking. None of this is built yet. |
| `swap_medipipe_to_yolo.md` | The MediaPipe→YOLO migration plan. | Partially done — YOLO drives 2D, but MediaPipe was kept for 3D (the doc assumed full removal). Says YOLOv8m; reality is YOLOv8n. |
| `walkthrough.md` | Note announcing the 3D world view (YOLO 2D + MediaPipe 3D side-by-side). | Accurate about the dual-engine 3D feature. |
| `README.md` | Public-facing overview + quick start. | Quick-start commands OK; the "Ball Tracker / Court Detector / shot classification" analytics bullets describe **orphaned** code (see [orphaned_code.md](orphaned_code.md)). |

## Realistic near-term progression

1. **Wire up existing orphaned analytics** — ball tracking, court homography,
   shot classification, movement/metrics already exist as code; connect them into
   `analyzer.py` (pass 1) → analysis JSON → frontend panels (the orphaned
   `MiniCourt`, `SpeedGauge`, `ShotPlacementChart`, `MetricsGrid` are waiting).
   See [orphaned_code.md](orphaned_code.md).
2. **GPU for faster pass-1 processing** — see [performance_and_hardware.md](performance_and_hardware.md).
3. **Multi-camera + triangulation**, then **sensor fusion**, then **Jetson/TensorRT**
   edge deployment — the `full_system_roadmap.md` arc.

When a request implies one of these, ground it in the current pipeline
([pipeline.md](pipeline.md)) and the orphaned building blocks rather than the
forward-looking root docs.
