"""
Shot Classifier — Rule-based tennis shot classification using pose keypoints
and ball proximity. Classifies forehand, backhand, serve, and volley.
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple
from config import KP
from utils.geometry import euclidean_distance


class ShotClassifier:
    """
    Classifies tennis strokes from player pose and ball position.
    Uses geometric rules based on arm position, ball height,
    and court position rather than a trained model (MVP approach).
    """

    def __init__(self):
        self._shot_counts: Dict[str, int] = {
            "forehand": 0,
            "backhand": 0,
            "serve": 0,
            "volley": 0,
        }
        self._last_shot: Optional[str] = None
        self._shot_history: list = []
        self._frames_since_shot = 0
        self._min_frames_between_shots = 15  # debounce

    def classify(
        self,
        keypoints: np.ndarray,
        ball_position: Optional[Tuple[float, float]],
        court_zone: str = "unknown",
        confidence_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Classify the current shot type.

        Returns:
            type: "forehand" | "backhand" | "serve" | "volley" | "unknown"
            confidence: 0.0 - 1.0
            is_new_shot: bool — True if this is a newly detected shot event
            counts: dict of cumulative shot counts
        """
        self._frames_since_shot += 1

        # Check if player is in a shot-making posture
        shot_type, confidence = self._detect_shot(
            keypoints, ball_position, court_zone, confidence_threshold
        )

        is_new = False
        if (shot_type != "unknown" and
                confidence > 0.5 and
                self._frames_since_shot >= self._min_frames_between_shots):
            is_new = True
            self._frames_since_shot = 0
            self._last_shot = shot_type
            self._shot_counts[shot_type] += 1
            self._shot_history.append(shot_type)

        return {
            "type": shot_type if shot_type != "unknown" else (self._last_shot or "unknown"),
            "confidence": round(confidence, 2),
            "is_new_shot": is_new,
            "counts": dict(self._shot_counts),
        }

    def _detect_shot(
        self,
        kps: np.ndarray,
        ball_pos: Optional[Tuple[float, float]],
        court_zone: str,
        conf_thresh: float,
    ) -> Tuple[str, float]:
        """
        Determine shot type from body pose geometry.

        Heuristics:
        - Serve: ball above head + arm extended upward
        - Volley: near net + compact arm position
        - Forehand: dominant wrist on dominant side relative to body center
        - Backhand: dominant wrist crosses to opposite side
        """
        # Check if we have enough keypoints
        required = [
            KP["left_shoulder"], KP["right_shoulder"],
            KP["left_wrist"], KP["right_wrist"],
            KP["left_hip"], KP["right_hip"],
            KP["nose"],
        ]
        if not all(kps[idx][2] >= conf_thresh for idx in required):
            return ("unknown", 0.0)

        nose = kps[KP["nose"]][:2]
        l_shoulder = kps[KP["left_shoulder"]][:2]
        r_shoulder = kps[KP["right_shoulder"]][:2]
        l_wrist = kps[KP["left_wrist"]][:2]
        r_wrist = kps[KP["right_wrist"]][:2]
        l_hip = kps[KP["left_hip"]][:2]
        r_hip = kps[KP["right_hip"]][:2]

        body_center_x = (l_shoulder[0] + r_shoulder[0]) / 2
        body_center_y = (l_shoulder[1] + r_shoulder[1]) / 2
        hip_center_y = (l_hip[1] + r_hip[1]) / 2
        body_height = abs(hip_center_y - body_center_y)

        # ── Serve Detection ──
        # Both wrists above shoulder level AND ball above head
        wrists_above = (l_wrist[1] < body_center_y or r_wrist[1] < body_center_y)
        highest_wrist_y = min(l_wrist[1], r_wrist[1])
        arm_extended_up = highest_wrist_y < nose[1] - body_height * 0.3

        if ball_pos:
            ball_above = ball_pos[1] < nose[1] - body_height * 0.5
        else:
            ball_above = False

        if arm_extended_up and (ball_above or wrists_above):
            return ("serve", 0.75)

        # ── Volley Detection ──
        # Near the net + compact arm position (wrists close to body)
        if "net" in court_zone:
            l_dist = euclidean_distance(l_wrist, np.array([body_center_x, body_center_y]))
            r_dist = euclidean_distance(r_wrist, np.array([body_center_x, body_center_y]))
            if l_dist < body_height * 1.2 and r_dist < body_height * 1.2:
                return ("volley", 0.65)

        # ── Forehand vs Backhand ──
        # Determine which wrist is more extended (likely the hitting arm)
        l_extension = euclidean_distance(l_wrist, l_shoulder)
        r_extension = euclidean_distance(r_wrist, r_shoulder)

        # The more extended arm is the hitting arm
        if r_extension > l_extension:
            hitting_wrist = r_wrist
            hitting_side = "right"
        else:
            hitting_wrist = l_wrist
            hitting_side = "left"

        # Check if hitting arm is extended enough to be a stroke
        max_ext = max(l_extension, r_extension)
        if max_ext < body_height * 0.6:
            return ("unknown", 0.2)

        # Forehand: hitting wrist is on the same side as the hitting arm
        # Backhand: hitting wrist crosses to the opposite side
        if hitting_side == "right":
            if hitting_wrist[0] > body_center_x:
                return ("forehand", 0.7)
            else:
                return ("backhand", 0.7)
        else:
            if hitting_wrist[0] < body_center_x:
                return ("forehand", 0.7)
            else:
                return ("backhand", 0.7)

    @property
    def total_shots(self) -> int:
        return sum(self._shot_counts.values())

    @property
    def shot_ratios(self) -> Dict[str, float]:
        total = self.total_shots
        if total == 0:
            return {k: 0.0 for k in self._shot_counts}
        return {k: round(v / total, 2) for k, v in self._shot_counts.items()}

    def reset(self):
        """Reset for new video."""
        self._shot_counts = {k: 0 for k in self._shot_counts}
        self._last_shot = None
        self._shot_history.clear()
        self._frames_since_shot = 0
