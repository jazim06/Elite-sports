"""
Pose Estimator — YOLO26-Pose (2D, COCO 17-keypoint format) + MediaPipe (3D)

This class runs TWO engines per frame:
  - YOLO26n-pose  → 2D keypoints for the video overlay (17 COCO keypoints)
  - MediaPipe Pose → 3D world landmarks (33), the source of the 3D view + angles

WHY YOLO26-Pose FOR 2D:
──────────────────────────────────────
- ~31-43% faster CPU inference than YOLOv8n (our main constraint on Intel Mac)
- More accurate keypoint localization (RLE) — better on fast/occluded swings
- COCO-trained: robust to diverse human poses and camera angles
- Same 17 COCO keypoints as YOLOv8 → drop-in (no data-contract change)
- CoreML-exportable for the planned on-device iPhone path

NOTE: MediaPipe is the *temporary* 3D source. It is a single-camera monocular
*estimate*, not triangulation, and is slated for removal in Phase 1c once
multi-camera triangulation provides metric 3D + joint angles (see plan).

COCO 17 KEYPOINTS:
  0: nose         5: left_shoulder   11: left_hip
  1: left_eye     6: right_shoulder  12: right_hip
  2: right_eye    7: left_elbow      13: left_knee
  3: left_ear     8: right_elbow     14: right_knee
  4: right_ear    9: left_wrist      15: left_ankle
                  10: right_wrist    16: right_ankle
"""

import os
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
import ssl

from config import POSE_EXPORT_FORMAT, POSE_IMGSZ

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


# Exported-artifact filename per format (relative to CWD, like the .pt weights)
_EXPORT_ARTIFACT = {
    "openvino": lambda base: f"{base}_openvino_model",
    "onnx": lambda base: f"{base}.onnx",
    "coreml": lambda base: f"{base}.mlpackage",
    "engine": lambda base: f"{base}.engine",  # TensorRT
}


def _load_pose_model(model_name: str, export_format: str, imgsz: int):
    """
    Load the YOLO pose model, optionally via a faster exported runtime.

    YOLO26's CPU speedup only materializes in an exported backend (OpenVINO/ONNX/
    CoreML/TensorRT), not raw PyTorch eager mode. The exported artifact is built
    once on first load and cached next to the weights; later runs reuse it.
    Falls back to raw PyTorch if export is disabled or fails.
    """
    if not export_format:
        return YOLO(model_name)

    base = model_name[:-3] if model_name.endswith(".pt") else model_name
    artifact_fn = _EXPORT_ARTIFACT.get(export_format)
    if artifact_fn is None:
        print(f"⚠️  Unknown POSE_EXPORT_FORMAT '{export_format}', using raw PyTorch.")
        return YOLO(model_name)

    artifact = artifact_fn(base)
    if os.path.exists(artifact):
        return YOLO(artifact, task="pose")

    try:
        print(f"⏳ Exporting {model_name} → {export_format} (one-time, imgsz={imgsz})…")
        exported = YOLO(model_name).export(format=export_format, imgsz=imgsz, verbose=False)
        return YOLO(exported, task="pose")
    except Exception as e:  # robust fallback — never break startup over an export
        print(f"⚠️  {export_format} export failed ({e}); falling back to raw PyTorch.")
        return YOLO(model_name)


class Pose3DEstimator:
    """
    YOLO-Pose (2D) + MediaPipe (3D) pose estimator.

    The class name is kept for backward compatibility. It uses YOLO26n-pose for
    2D keypoint detection and MediaPipe for the 3D world landmarks that drive the
    3D view and joint-angle math.
    """

    def __init__(self, model_name: str = "yolo26n-pose.pt",
                 export_format: str = POSE_EXPORT_FORMAT, imgsz: int = POSE_IMGSZ):
        """
        Load the YOLO pose model (via an exported runtime for CPU speed) + MediaPipe.

        Args:
            model_name: Ultralytics pose model. Options:
                - yolo26n-pose.pt  (nano, fastest — current default)
                - yolo26s-pose.pt / yolo26m-pose.pt / yolo26l-pose.pt (more accurate)
                - yolov8n-pose.pt  (previous engine; still supported)
            export_format: inference backend (see config.POSE_EXPORT_FORMAT).
                "" → raw PyTorch; "openvino"/"onnx"/"coreml"/"engine" → exported.
            imgsz: square export size (letterboxes any aspect ratio).
        """
        print(f"⏳ Loading YOLO-Pose model: {model_name} (backend: {export_format or 'pytorch'})")
        self.model = _load_pose_model(model_name, export_format, imgsz)
        print(f"✅ YOLO-Pose loaded: {model_name}")

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
