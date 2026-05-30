"""
Pose Estimator — YOLOv8-Pose for player detection and skeletal keypoint extraction.
Combines detection + pose in a single model pass for efficiency.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from ultralytics import YOLO
from config import POSE_MODEL, CONFIDENCE_THRESHOLD, PERSON_CLASS_ID, KEYPOINT_NAMES


class PoseEstimator:
    """
    Wraps YOLOv8-Pose to detect players and extract 17-joint COCO skeletons.
    """

    def __init__(self, model_path: str = POSE_MODEL, device: str = "auto"):
        """
        Initialize the pose estimation model.
        device: 'auto' (picks best available), 'cpu', 'cuda', 'mps'
        """
        self.model = YOLO(model_path)
        self._device = device
        self._frame_count = 0

    def process_frame(
        self,
        frame: np.ndarray,
        confidence: float = CONFIDENCE_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """
        Run pose estimation on a single frame.

        Returns a list of player dicts:
        {
            "id": int,
            "bbox": [x1, y1, x2, y2],
            "confidence": float,
            "keypoints": np.ndarray (17, 3) — [x, y, conf] per keypoint,
            "keypoints_dict": dict mapping keypoint name → (x, y, conf),
        }
        """
        self._frame_count += 1

        # Run inference with tracking enabled for persistent IDs
        results = self.model.track(
            frame,
            persist=True,
            conf=confidence,
            iou=0.45,
            classes=[PERSON_CLASS_ID],
            verbose=False,
            device=self._resolve_device(),
        )

        players = []
        if results and len(results) > 0:
            result = results[0]

            # Extract boxes
            boxes = result.boxes
            keypoints_data = result.keypoints

            if boxes is not None and len(boxes) > 0:
                for i in range(len(boxes)):
                    # Bounding box
                    bbox = boxes.xyxy[i].cpu().numpy().tolist()

                    # Track ID (if available)
                    track_id = int(boxes.id[i]) if boxes.id is not None else i + 1

                    # Confidence
                    conf = float(boxes.conf[i])

                    # Keypoints (17, 3) — x, y, confidence
                    kps = None
                    kps_dict = {}
                    if keypoints_data is not None and i < len(keypoints_data):
                        kps_xy = keypoints_data.xy[i].cpu().numpy()   # (17, 2)
                        kps_conf = keypoints_data.conf[i].cpu().numpy()  # (17,)
                        kps = np.column_stack([kps_xy, kps_conf])  # (17, 3)

                        # Build named dict
                        for idx, name in enumerate(KEYPOINT_NAMES):
                            kps_dict[name] = {
                                "x": float(kps[idx][0]),
                                "y": float(kps[idx][1]),
                                "confidence": float(kps[idx][2]),
                            }

                    players.append({
                        "id": track_id,
                        "bbox": bbox,
                        "confidence": conf,
                        "keypoints": kps,
                        "keypoints_dict": kps_dict,
                    })

        return players

    def _resolve_device(self) -> str:
        """Resolve the best available device."""
        if self._device != "auto":
            return self._device
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def reset(self):
        """Reset tracker state between videos."""
        self._frame_count = 0
        self.model.predictor = None
