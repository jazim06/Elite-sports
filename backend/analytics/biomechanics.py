"""
Biomechanics Calculator — Computes joint angles, angular velocity,
trunk lean, and body symmetry from pose keypoints.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from config import KP
from utils.geometry import joint_angle, euclidean_distance, midpoint


class BiomechanicsCalculator:
    """
    Computes biomechanical metrics from COCO 17-keypoint pose data.
    Maintains per-player history for angular velocity calculation.
    """

    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self._history: Dict[int, List[Dict]] = {}  # player_id → list of angle dicts
        self._max_history = 30  # keep last N frames per player

    def compute(
        self,
        player_id: int,
        keypoints: np.ndarray,
        confidence_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Compute all biomechanical metrics for a player's pose.

        keypoints: (17, 3) array of [x, y, confidence].

        Returns dict with:
            joint_angles: dict of angle name → degrees
            angular_velocity: dict of angle name → deg/sec
            trunk_lean: float (degrees from vertical)
            body_symmetry: dict with symmetry scores
        """
        angles = self._compute_joint_angles(keypoints, confidence_threshold)
        angular_vel = self._compute_angular_velocity(player_id, angles)
        trunk_lean = self._compute_trunk_lean(keypoints, confidence_threshold)
        symmetry = self._compute_symmetry(angles)

        # Store history
        if player_id not in self._history:
            self._history[player_id] = []
        self._history[player_id].append(angles)
        if len(self._history[player_id]) > self._max_history:
            self._history[player_id] = self._history[player_id][-self._max_history:]

        return {
            "joint_angles": angles,
            "angular_velocity": angular_vel,
            "trunk_lean": trunk_lean,
            "body_symmetry": symmetry,
        }

    def _compute_joint_angles(
        self,
        kps: np.ndarray,
        conf_thresh: float,
    ) -> Dict[str, float]:
        """Compute major joint angles from keypoints."""
        angles = {}

        def _safe_angle(a_idx: int, b_idx: int, c_idx: int, name: str):
            """Compute angle if all three keypoints are confident."""
            if (kps[a_idx][2] >= conf_thresh and
                    kps[b_idx][2] >= conf_thresh and
                    kps[c_idx][2] >= conf_thresh):
                a = kps[a_idx][:2]
                b = kps[b_idx][:2]
                c = kps[c_idx][:2]
                angles[name] = round(joint_angle(a, b, c), 1)

        # ── Left side ──
        _safe_angle(KP["left_shoulder"], KP["left_elbow"], KP["left_wrist"], "elbow_left")
        _safe_angle(KP["left_hip"], KP["left_knee"], KP["left_ankle"], "knee_left")
        _safe_angle(KP["left_elbow"], KP["left_shoulder"], KP["left_hip"], "shoulder_left")
        _safe_angle(KP["left_knee"], KP["left_hip"], KP["left_shoulder"], "hip_left")

        # ── Right side ──
        _safe_angle(KP["right_shoulder"], KP["right_elbow"], KP["right_wrist"], "elbow_right")
        _safe_angle(KP["right_hip"], KP["right_knee"], KP["right_ankle"], "knee_right")
        _safe_angle(KP["right_elbow"], KP["right_shoulder"], KP["right_hip"], "shoulder_right")
        _safe_angle(KP["right_knee"], KP["right_hip"], KP["right_shoulder"], "hip_right")

        return angles

    def _compute_angular_velocity(
        self,
        player_id: int,
        current_angles: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute angular velocity (deg/sec) from the change in angle
        between the current and previous frame.
        """
        velocities = {}
        history = self._history.get(player_id, [])

        if len(history) < 1:
            return velocities

        prev_angles = history[-1]
        dt = 1.0 / self.fps if self.fps > 0 else 1.0

        for name, current_val in current_angles.items():
            if name in prev_angles:
                delta = abs(current_val - prev_angles[name])
                velocities[name] = round(delta / dt, 1)

        return velocities

    def _compute_trunk_lean(
        self,
        kps: np.ndarray,
        conf_thresh: float,
    ) -> Optional[float]:
        """
        Compute trunk lean angle — how far the torso leans from vertical.
        Uses the midpoint of shoulders and midpoint of hips to define the trunk axis.
        """
        ls, rs = KP["left_shoulder"], KP["right_shoulder"]
        lh, rh = KP["left_hip"], KP["right_hip"]

        if (kps[ls][2] >= conf_thresh and kps[rs][2] >= conf_thresh and
                kps[lh][2] >= conf_thresh and kps[rh][2] >= conf_thresh):
            shoulder_mid = midpoint(kps[ls][:2], kps[rs][:2])
            hip_mid = midpoint(kps[lh][:2], kps[rh][:2])

            # Trunk vector (hip → shoulder)
            trunk_vec = shoulder_mid - hip_mid
            # Vertical reference (pointing up in image coords = negative y)
            vertical = np.array([0, -1])

            # Angle between trunk and vertical
            cos_angle = np.dot(trunk_vec, vertical) / (
                np.linalg.norm(trunk_vec) * np.linalg.norm(vertical) + 1e-8
            )
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            lean_angle = float(np.degrees(np.arccos(cos_angle)))

            return round(lean_angle, 1)

        return None

    def _compute_symmetry(self, angles: Dict[str, float]) -> Dict[str, Any]:
        """
        Compare left vs right side angles to detect asymmetry.
        Returns symmetry scores (0 = perfect, higher = more asymmetric).
        """
        pairs = [
            ("elbow_left", "elbow_right"),
            ("knee_left", "knee_right"),
            ("shoulder_left", "shoulder_right"),
            ("hip_left", "hip_right"),
        ]

        symmetry = {}
        total_diff = 0
        count = 0

        for left, right in pairs:
            if left in angles and right in angles:
                diff = abs(angles[left] - angles[right])
                name = left.replace("_left", "")
                symmetry[name] = round(diff, 1)
                total_diff += diff
                count += 1

        symmetry["overall"] = round(total_diff / max(count, 1), 1)
        return symmetry

    def reset(self):
        """Reset history for new video."""
        self._history.clear()
