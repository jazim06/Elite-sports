"""
Pose Estimator — YOLOv8m-Pose (COCO 17-keypoint format)

WHY YOLOv8-Pose INSTEAD OF MEDIAPIPE:
──────────────────────────────────────
- Significantly more accurate joint localization for sports
- Better handles occlusion, fast movement, and unusual angles
- COCO-trained: robust to diverse human poses and camera angles
- The medium variant (yolov8m-pose) is the sweet spot for accuracy vs speed
- Built-in tracking (BoTSORT) for multi-person scenarios

COCO 17 KEYPOINTS:
  0: nose         5: left_shoulder   11: left_hip
  1: left_eye     6: right_shoulder  12: right_hip
  2: right_eye    7: left_elbow      13: left_knee
  3: left_ear     8: right_elbow     14: right_knee
  4: right_ear    9: left_wrist      15: left_ankle
                  10: right_wrist    16: right_ankle
"""

import numpy as np
from ultralytics import YOLO
import mediapipe as mp
import ssl

# Fix for macOS Python SSL Certificate errors when MediaPipe downloads models
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


# COCO keypoint names, indexed 0-16
COCO_KEYPOINT_NAMES = [
    "nose",
    "left_eye", "right_eye",
    "left_ear", "right_ear",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
]

# Map to uppercase format used by kinematics engine and frontend
COCO_TO_UPPER = {name: name.upper() for name in COCO_KEYPOINT_NAMES}


class Pose3DEstimator:
    """
    YOLOv8-Pose based pose estimator.
    
    Despite the class name (kept for backward compatibility), this now uses
    YOLOv8m-Pose for 2D keypoint detection. The 'z' coordinate is set to 0
    since YOLO provides 2D keypoints — but the angle calculations still work
    correctly because the kinematics engine uses 3D vectors and the z=0 case
    degenerates to a 2D angle calculation.
    """

    def __init__(self, model_name: str = "yolov8n-pose.pt"):
        """
        Load YOLOv8-Pose model.
        
        Args:
            model_name: Model variant. Options:
                - yolov8n-pose.pt  (nano, ~7MB, fastest)
                - yolov8s-pose.pt  (small, ~24MB)
                - yolov8m-pose.pt  (medium, ~50MB, best balance)
                - yolov8l-pose.pt  (large, ~84MB, most accurate)
        """
        print(f"⏳ Loading YOLOv8-Pose model: {model_name}")
        self.model = YOLO(model_name)
        print(f"✅ YOLOv8-Pose loaded: {model_name}")

        print("⏳ Loading MediaPipe Pose for 3D World coordinates...")
        self.mp_pose = mp.solutions.pose
        self.pose_3d = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("✅ MediaPipe Pose loaded.")

    def process_frame(self, frame_bgr):
        """
        Process a single frame and extract pose keypoints.

        Args:
            frame_bgr: OpenCV image (BGR format)

        Returns:
            dict with 'landmarks_3d' and 'landmarks_2d'
            or None if no person detected.
        """
        # Run inference (YOLO handles BGR natively)
        results = self.model(frame_bgr, verbose=False)

        if not results or len(results) == 0:
            return None

        result = results[0]

        # Check if any keypoints were detected
        if result.keypoints is None or len(result.keypoints) == 0:
            return None

        # Get the keypoints for the person with the largest bounding box
        # (most likely the main player in a tennis video)
        keypoints = result.keypoints
        
        if keypoints.xy is None or keypoints.xy.shape[0] == 0:
            return None

        # Select the person with the largest bounding box area
        if result.boxes is not None and len(result.boxes) > 1:
            areas = (result.boxes.xyxy[:, 2] - result.boxes.xyxy[:, 0]) * \
                    (result.boxes.xyxy[:, 3] - result.boxes.xyxy[:, 1])
            best_idx = int(areas.argmax())
        else:
            best_idx = 0

        # ── 1. Run YOLOv8 for 2D Keypoints ──
        # keypoints.xy: (N, 17, 2) — pixel coordinates
        # keypoints.conf: (N, 17) — confidence scores
        kp_xy = keypoints.xy[best_idx].cpu().numpy()       # (17, 2)
        kp_conf = keypoints.conf[best_idx].cpu().numpy() if keypoints.conf is not None else np.ones(17)  # (17,)

        h, w = frame_bgr.shape[:2]

        landmarks_2d = {}
        for idx in range(17):
            name = COCO_TO_UPPER[COCO_KEYPOINT_NAMES[idx]]
            px, py = float(kp_xy[idx, 0]), float(kp_xy[idx, 1])
            conf = float(kp_conf[idx])

            # Skip keypoints with zero coordinates (not detected)
            if px == 0 and py == 0:
                conf = 0.0

            # Normalized coordinates (0.0–1.0)
            nx = px / w if w > 0 else 0.0
            ny = py / h if h > 0 else 0.0

            # 2D landmarks for frontend overlay
            landmarks_2d[name] = {
                "x": nx,
                "y": ny,
                "visibility": conf,
            }

        # ── 2. Run MediaPipe for 3D Keypoints ──
        import cv2
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_results = self.pose_3d.process(frame_rgb)
        
        landmarks_3d = {}
        if mp_results.pose_world_landmarks:
            for idx, lm in enumerate(mp_results.pose_world_landmarks.landmark):
                try:
                    name = self.mp_pose.PoseLandmark(idx).name
                    landmarks_3d[name] = {
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z,
                        "visibility": lm.visibility
                    }
                except ValueError:
                    continue
        else:
            # Fallback: if MediaPipe fails, populate with YOLO (z=0) so the app doesn't crash
            for name, pt in landmarks_2d.items():
                landmarks_3d[name] = {"x": pt["x"], "y": pt["y"], "z": 0.0, "visibility": pt["visibility"]}

        return {
            "landmarks_3d": landmarks_3d,
            "landmarks_2d": landmarks_2d,
        }
