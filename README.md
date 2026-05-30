# 🎾 Tennia — Elite Tennis Analytics

Real-time tennis analytics powered by computer vision. Upload iPhone video footage and get instant player tracking, biomechanics analysis, ball trajectory, and performance metrics.

## Architecture

```
iPhone Video → FastAPI Backend → YOLOv8-Pose + Ball Tracker → WebSocket → React Dashboard
```

### Backend (Python)
- **FastAPI** — Async HTTP + WebSocket server
- **YOLOv8-Pose** — Player detection + 17-joint skeletal pose estimation
- **Ball Tracker** — YOLOv8 + HSV fallback + Kalman filter trajectory smoothing
- **Court Detector** — Hough lines + homography for real-world coordinate mapping
- **Analytics Engine** — Joint angles, speed, distance, shot classification, rally tracking

### Frontend (React + TypeScript)
- **Video Canvas** — Streams annotated frames with skeleton overlays
- **Biomechanics Panel** — Joint angle bars with status coloring
- **Speed Gauge** — SVG radial gauge for ball/player speed
- **Mini Court** — Top-down SVG court radar with live positions
- **Shot Placement** — Scatter chart of shot landing positions
- **Metrics Grid** — KPI cards for session stats

## Quick Start

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Backend Server

```bash
cd backend
python main.py
```

The server starts at `http://localhost:8000`.

> **Note:** First run downloads YOLOv8 models (~6MB each). GPU acceleration is automatic on CUDA/MPS.

### 3. Start Frontend Dev Server

```bash
cd frontend
npm install
npm run dev
```

The dashboard opens at `http://localhost:5173`.

### 4. Upload & Analyze

1. Open the dashboard in your browser
2. Drag & drop a tennis video (.mp4/.mov from iPhone)
3. Watch the CV pipeline analyze every frame in real-time
4. View biomechanics, ball tracking, and performance metrics live

## iPhone Recording Tips

- **Resolution:** 1080p at 60fps (Settings → Camera → Record Video)
- **Position:** Mount at elevation (8-15m high) at baseline corner
- **Stability:** Use a tripod with phone mount
- **Lighting:** Shoot with the sun behind the camera

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11+ |
| CV Models | Ultralytics YOLOv8 |
| Tracking | BoTSORT (via Ultralytics) |
| Ball Filter | OpenCV Kalman Filter |
| Court Detection | OpenCV Hough + Homography |
| Frontend | Vite, React, TypeScript |
| Real-time | WebSocket |
| Styling | Vanilla CSS (custom design system) |

## License

MIT
