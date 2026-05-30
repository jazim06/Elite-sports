"""
Movement Analytics — Computes player speed, acceleration, distance,
court coverage heatmap, and zone classification.
"""
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from config import KP, COURT_LENGTH, COURT_WIDTH, NET_TO_BASELINE
from utils.geometry import euclidean_distance, midpoint, pixel_speed_to_real


class MovementAnalyzer:
    """
    Tracks player movement metrics over time.
    Maintains per-player position history for cumulative calculations.
    """

    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self._positions: Dict[int, List[Tuple[float, float]]] = {}
        self._court_positions: Dict[int, List[Tuple[float, float]]] = {}
        self._distances: Dict[int, float] = {}  # cumulative in meters
        self._max_speeds: Dict[int, float] = {}
        self._heatmap_data: Dict[int, List[Tuple[float, float]]] = {}

    def compute(
        self,
        player_id: int,
        keypoints: np.ndarray,
        homography: Optional[np.ndarray] = None,
        scale_factor: float = 50.0,
        confidence_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Compute movement metrics for a player.

        Returns:
            speed_kmh: current speed in km/h
            max_speed_kmh: session maximum speed
            acceleration: current acceleration in m/s²
            distance_m: total distance covered in meters
            court_position: (x, y) in court coordinates if calibrated
            zone: str — which court zone the player is in
            heatmap: accumulated position data
        """
        # Get player center from hip midpoint (most stable for position)
        lh, rh = KP["left_hip"], KP["right_hip"]
        la, ra = KP["left_ankle"], KP["right_ankle"]

        # Prefer hip midpoint, fallback to ankle midpoint
        if (keypoints[lh][2] >= confidence_threshold and
                keypoints[rh][2] >= confidence_threshold):
            center_px = midpoint(keypoints[lh][:2], keypoints[rh][:2])
        elif (keypoints[la][2] >= confidence_threshold and
                keypoints[ra][2] >= confidence_threshold):
            center_px = midpoint(keypoints[la][:2], keypoints[ra][:2])
        else:
            return self._empty_result(player_id)

        center_px_tuple = (float(center_px[0]), float(center_px[1]))

        # Init history
        if player_id not in self._positions:
            self._positions[player_id] = []
            self._court_positions[player_id] = []
            self._distances[player_id] = 0.0
            self._max_speeds[player_id] = 0.0
            self._heatmap_data[player_id] = []

        # Calculate pixel displacement
        prev = self._positions[player_id][-1] if self._positions[player_id] else None
        pixel_disp = 0.0
        if prev:
            pixel_disp = euclidean_distance(
                np.array(center_px_tuple), np.array(prev)
            )

        # Convert to real speed
        speed_kmh = pixel_speed_to_real(pixel_disp, homography, self.fps, scale_factor)

        # Filter out noise (small movements < 0.5 km/h are likely jitter)
        if speed_kmh < 0.5:
            speed_kmh = 0.0

        # Update max speed
        self._max_speeds[player_id] = max(self._max_speeds[player_id], speed_kmh)

        # Calculate acceleration
        acceleration = 0.0
        if len(self._positions[player_id]) >= 2:
            prev2 = self._positions[player_id][-2]
            prev_disp = euclidean_distance(np.array(prev), np.array(prev2))
            prev_speed = pixel_speed_to_real(prev_disp, homography, self.fps, scale_factor)
            dt = 1.0 / self.fps if self.fps > 0 else 1.0
            speed_ms = speed_kmh / 3.6
            prev_speed_ms = prev_speed / 3.6
            acceleration = round((speed_ms - prev_speed_ms) / dt, 2)

        # Update cumulative distance
        meters_per_frame = (speed_kmh / 3.6) / self.fps if self.fps > 0 else 0
        self._distances[player_id] += meters_per_frame

        # Court position (if calibrated)
        court_pos = None
        zone = "unknown"
        if homography is not None:
            pt = np.array([center_px_tuple[0], center_px_tuple[1], 1.0])
            transformed = homography @ pt
            transformed /= transformed[2] + 1e-8
            court_pos = (round(float(transformed[0]), 2), round(float(transformed[1]), 2))
            zone = self._classify_zone(court_pos)
            self._court_positions[player_id].append(court_pos)

        # Update position history
        self._positions[player_id].append(center_px_tuple)
        if len(self._positions[player_id]) > 300:
            self._positions[player_id] = self._positions[player_id][-300:]

        # Heatmap data
        self._heatmap_data[player_id].append(
            court_pos if court_pos else center_px_tuple
        )

        return {
            "speed_kmh": round(speed_kmh, 1),
            "max_speed_kmh": round(self._max_speeds[player_id], 1),
            "acceleration_ms2": acceleration,
            "distance_m": round(self._distances[player_id], 1),
            "position_px": center_px_tuple,
            "court_position": court_pos,
            "zone": zone,
        }

    def _classify_zone(self, court_pos: Tuple[float, float]) -> str:
        """Classify court position into named zones."""
        x, y = court_pos

        # Check if within court bounds (with margin)
        if x < -1 or x > COURT_WIDTH + 1 or y < -1 or y > COURT_LENGTH + 1:
            return "out_of_court"

        half = COURT_LENGTH / 2

        if y < half:
            # Top half of court
            if y < half - 6.4:
                return "baseline_far"
            elif y < half - 3:
                return "midcourt_far"
            else:
                return "net_far"
        else:
            # Bottom half of court
            if y > half + 6.4:
                return "baseline_near"
            elif y > half + 3:
                return "midcourt_near"
            else:
                return "net_near"

    def _empty_result(self, player_id: int) -> Dict[str, Any]:
        return {
            "speed_kmh": 0.0,
            "max_speed_kmh": self._max_speeds.get(player_id, 0.0),
            "acceleration_ms2": 0.0,
            "distance_m": self._distances.get(player_id, 0.0),
            "position_px": None,
            "court_position": None,
            "zone": "unknown",
        }

    def get_heatmap(self, player_id: int) -> List[Tuple[float, float]]:
        """Get accumulated heatmap data for a player."""
        return self._heatmap_data.get(player_id, [])

    def reset(self):
        """Reset all tracking state."""
        self._positions.clear()
        self._court_positions.clear()
        self._distances.clear()
        self._max_speeds.clear()
        self._heatmap_data.clear()
