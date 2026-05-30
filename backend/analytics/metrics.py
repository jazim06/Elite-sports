"""
Aggregate Metrics — Collects and computes session-level match statistics.
"""
from typing import Dict, Any, List
from collections import defaultdict


class MetricsAggregator:
    """
    Aggregates per-frame analytics into session-level metrics.
    """

    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self._frame_count = 0
        self._ball_speeds: List[float] = []
        self._player_speeds: Dict[int, List[float]] = defaultdict(list)
        self._shot_events: List[Dict] = []
        self._rally_lengths: List[int] = []
        self._current_rally = 0
        self._frames_since_ball_hit = 0

    def update(
        self,
        players: List[Dict[str, Any]],
        ball: Dict[str, Any],
        shot: Dict[str, Any],
    ):
        """Update metrics with data from a processed frame."""
        self._frame_count += 1

        # Ball speed
        if ball.get("speed_kmh", 0) > 0:
            self._ball_speeds.append(ball["speed_kmh"])

        # Player speeds
        for player in players:
            pid = player.get("id", 0)
            speed = player.get("speed_kmh", 0)
            if speed > 0:
                self._player_speeds[pid].append(speed)

        # Shot events and rally tracking
        if shot.get("is_new_shot", False):
            self._shot_events.append({
                "frame": self._frame_count,
                "type": shot["type"],
                "confidence": shot["confidence"],
            })
            self._current_rally += 1
            self._frames_since_ball_hit = 0
        else:
            self._frames_since_ball_hit += 1
            # If no shot for ~3 seconds, rally is over
            if (self._frames_since_ball_hit > self.fps * 3 and
                    self._current_rally > 0):
                self._rally_lengths.append(self._current_rally)
                self._current_rally = 0

    def get_summary(self) -> Dict[str, Any]:
        """
        Get aggregated session metrics.
        """
        duration_sec = self._frame_count / self.fps if self.fps > 0 else 0

        # Ball speed stats
        avg_ball_speed = (
            round(sum(self._ball_speeds) / len(self._ball_speeds), 1)
            if self._ball_speeds else 0.0
        )
        max_ball_speed = (
            round(max(self._ball_speeds), 1)
            if self._ball_speeds else 0.0
        )

        # Shot counts
        shot_counts = {"forehand": 0, "backhand": 0, "serve": 0, "volley": 0}
        for event in self._shot_events:
            t = event["type"]
            if t in shot_counts:
                shot_counts[t] += 1
        total_shots = sum(shot_counts.values())

        # Shots per hour
        shots_per_hour = (
            round(total_shots / (duration_sec / 3600), 0)
            if duration_sec > 0 else 0
        )

        # Rally stats
        all_rallies = self._rally_lengths[:]
        if self._current_rally > 0:
            all_rallies.append(self._current_rally)
        avg_rally = (
            round(sum(all_rallies) / len(all_rallies), 1)
            if all_rallies else 0.0
        )
        max_rally = max(all_rallies) if all_rallies else 0

        # Player distance
        player_distances = {}
        for pid, speeds in self._player_speeds.items():
            # Rough distance from accumulated speeds
            total_m = sum(s / 3.6 / self.fps for s in speeds)
            player_distances[pid] = round(total_m, 1)

        return {
            "duration_sec": round(duration_sec, 1),
            "total_frames": self._frame_count,
            "total_shots": total_shots,
            "shot_counts": shot_counts,
            "shots_per_hour": shots_per_hour,
            "avg_ball_speed_kmh": avg_ball_speed,
            "max_ball_speed_kmh": max_ball_speed,
            "avg_rally_length": avg_rally,
            "longest_rally": max_rally,
            "player_distances_m": player_distances,
        }

    def reset(self):
        """Reset for new session."""
        self._frame_count = 0
        self._ball_speeds.clear()
        self._player_speeds.clear()
        self._shot_events.clear()
        self._rally_lengths.clear()
        self._current_rally = 0
        self._frames_since_ball_hit = 0
