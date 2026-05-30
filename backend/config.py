"""
Tennia — Configuration constants for the CV pipeline and analytics engine.
"""
import os

# ── Paths ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── YOLO Models ────────────────────────────────────────
# Using nano variants for speed; swap to "m" or "l" for higher accuracy
POSE_MODEL = "yolov8n-pose.pt"
DETECT_MODEL = "yolov8n.pt"

# ── CV Pipeline ────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.5
BALL_CONFIDENCE_THRESHOLD = 0.3
IOU_THRESHOLD = 0.45

# Detection class IDs (COCO)
PERSON_CLASS_ID = 0
SPORTS_BALL_CLASS_ID = 32

# ── Court Dimensions (meters) ─────────────────────────
# Standard tennis court dimensions
COURT_LENGTH = 23.77   # full court length in meters
COURT_WIDTH = 10.97     # doubles court width
SINGLES_WIDTH = 8.23    # singles court width
SERVICE_LINE_DIST = 6.40  # distance from net to service line
NET_TO_BASELINE = 11.885  # half court length

# ── Analytics ──────────────────────────────────────────
# Joint angle thresholds (degrees) for biomechanics color coding
ANGLE_OPTIMAL_MIN = 120
ANGLE_OPTIMAL_MAX = 180
ANGLE_CAUTION_MIN = 90
ANGLE_CAUTION_MAX = 120
# Below 90 = injury risk zone

# ── Kalman Filter ──────────────────────────────────────
KALMAN_PROCESS_NOISE = 0.03
KALMAN_MEASUREMENT_NOISE = 0.5

# ── WebSocket ──────────────────────────────────────────
WS_FRAME_QUALITY = 70  # JPEG quality for WebSocket frame streaming (0-100)
MAX_FRAME_WIDTH = 1280  # Resize frames for processing efficiency

# ── COCO Keypoint Indices ──────────────────────────────
# YOLOv8-Pose uses 17 COCO keypoints
KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

# Keypoint index mapping
KP = {name: idx for idx, name in enumerate(KEYPOINT_NAMES)}

# Skeleton connections for drawing
SKELETON_CONNECTIONS = [
    (KP["left_shoulder"], KP["right_shoulder"]),
    (KP["left_shoulder"], KP["left_elbow"]),
    (KP["left_elbow"], KP["left_wrist"]),
    (KP["right_shoulder"], KP["right_elbow"]),
    (KP["right_elbow"], KP["right_wrist"]),
    (KP["left_shoulder"], KP["left_hip"]),
    (KP["right_shoulder"], KP["right_hip"]),
    (KP["left_hip"], KP["right_hip"]),
    (KP["left_hip"], KP["left_knee"]),
    (KP["left_knee"], KP["left_ankle"]),
    (KP["right_hip"], KP["right_knee"]),
    (KP["right_knee"], KP["right_ankle"]),
]
