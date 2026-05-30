"""
Ball Tracker — Detects tennis balls using YOLOv8 + color-based fallback,
then smooths trajectory with a Kalman filter.
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from ultralytics import YOLO
from config import (
    DETECT_MODEL, BALL_CONFIDENCE_THRESHOLD, SPORTS_BALL_CLASS_ID,
    KALMAN_PROCESS_NOISE, KALMAN_MEASUREMENT_NOISE,
)


class KalmanBallFilter:
    """
    2D Kalman filter for ball position smoothing and prediction.
    State: [x, y, vx, vy]
    Measurement: [x, y]
    """

    def __init__(self):
        self.kf = cv2.KalmanFilter(4, 2)
        # Transition matrix (constant velocity model)
        self.kf.transitionMatrix = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float32)

        # Measurement matrix
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=np.float32)

        # Process noise
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * KALMAN_PROCESS_NOISE

        # Measurement noise
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * KALMAN_MEASUREMENT_NOISE

        # Error covariance
        self.kf.errorCovPost = np.eye(4, dtype=np.float32)

        self._initialized = False
        self._frames_without_detection = 0
        self._max_miss_frames = 10

    def update(self, measurement: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        Update with a new measurement (detected ball position).
        Returns smoothed position or predicted position if no detection.
        """
        if measurement is not None:
            meas = np.array([[measurement[0]], [measurement[1]]], dtype=np.float32)

            if not self._initialized:
                self.kf.statePost = np.array([
                    [measurement[0]], [measurement[1]], [0], [0]
                ], dtype=np.float32)
                self._initialized = True
                self._frames_without_detection = 0
                return measurement

            self.kf.correct(meas)
            self.kf.predict()
            self._frames_without_detection = 0

            state = self.kf.statePost
            return (float(state[0]), float(state[1]))
        else:
            self._frames_without_detection += 1
            if self._initialized and self._frames_without_detection <= self._max_miss_frames:
                predicted = self.kf.predict()
                return (float(predicted[0]), float(predicted[1]))
            return None

    def get_velocity(self) -> Tuple[float, float]:
        """Get current estimated velocity (vx, vy) in pixels/frame."""
        if self._initialized:
            state = self.kf.statePost
            return (float(state[2]), float(state[3]))
        return (0.0, 0.0)

    def reset(self):
        """Reset the filter."""
        self.__init__()


class BallTracker:
    """
    Detects and tracks the tennis ball across frames.
    Uses YOLOv8 detection with HSV color fallback for robustness.
    """

    def __init__(self, model_path: str = DETECT_MODEL, device: str = "auto"):
        self.model = YOLO(model_path)
        self._device = device
        self.kalman = KalmanBallFilter()
        self.trajectory: List[Tuple[float, float]] = []
        self._prev_position: Optional[Tuple[float, float]] = None
        self._max_trajectory_len = 60

        # HSV range for yellow-green tennis ball
        self._ball_hsv_lower = np.array([25, 80, 80])
        self._ball_hsv_upper = np.array([50, 255, 255])

    def process_frame(
        self,
        frame: np.ndarray,
        confidence: float = BALL_CONFIDENCE_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Detect and track ball in a single frame.

        Returns:
        {
            "position": (x, y) or None,
            "raw_detection": (x, y) or None,
            "speed_px": float (pixels/frame),
            "speed_kmh": float (estimated, rough),
            "trajectory": [(x,y), ...],
            "detected": bool,
        }
        """
        raw_detection = self._detect_yolo(frame, confidence)

        # Fallback to HSV color detection if YOLO misses
        if raw_detection is None:
            raw_detection = self._detect_hsv(frame)

        # Update Kalman filter
        smoothed = self.kalman.update(raw_detection)

        # Calculate speed
        speed_px = 0.0
        if smoothed and self._prev_position:
            dx = smoothed[0] - self._prev_position[0]
            dy = smoothed[1] - self._prev_position[1]
            speed_px = np.sqrt(dx * dx + dy * dy)

        # Update trajectory
        if smoothed:
            self.trajectory.append(smoothed)
            if len(self.trajectory) > self._max_trajectory_len:
                self.trajectory = self.trajectory[-self._max_trajectory_len:]

        self._prev_position = smoothed

        return {
            "position": smoothed,
            "raw_detection": raw_detection,
            "speed_px": round(speed_px, 2),
            "speed_kmh": 0.0,  # Will be set by the analytics layer with court calibration
            "trajectory": list(self.trajectory),
            "detected": raw_detection is not None,
        }

    def _detect_yolo(
        self,
        frame: np.ndarray,
        confidence: float,
    ) -> Optional[Tuple[float, float]]:
        """Detect ball using YOLOv8."""
        results = self.model(
            frame,
            conf=confidence,
            classes=[SPORTS_BALL_CLASS_ID],
            verbose=False,
        )

        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                # Take highest confidence detection
                best_idx = boxes.conf.argmax()
                bbox = boxes.xyxy[best_idx].cpu().numpy()
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                return (float(cx), float(cy))

        return None

    def _detect_hsv(self, frame: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Fallback ball detection using HSV color thresholding.
        Works well for bright yellow-green tennis balls.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._ball_hsv_lower, self._ball_hsv_upper)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Filter by size (tennis ball should be small-to-medium)
            valid = []
            h, w = frame.shape[:2]
            min_area = (w * h) * 0.0001  # at least 0.01% of frame
            max_area = (w * h) * 0.01     # at most 1% of frame

            for c in contours:
                area = cv2.contourArea(c)
                if min_area <= area <= max_area:
                    # Check circularity
                    perimeter = cv2.arcLength(c, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        if circularity > 0.5:
                            valid.append((c, area))

            if valid:
                # Take the most circular / best candidate
                best = max(valid, key=lambda x: x[1])
                M = cv2.moments(best[0])
                if M["m00"] > 0:
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    return (float(cx), float(cy))

        return None

    def reset(self):
        """Reset tracker for a new video."""
        self.kalman.reset()
        self.trajectory.clear()
        self._prev_position = None

    def _resolve_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
