"""
Drawing utilities for annotating video frames with CV pipeline results.
Renders skeletons, ball trajectories, bounding boxes, and text overlays.
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from config import SKELETON_CONNECTIONS, KP


# ── Color Palette (BGR for OpenCV) ─────────────────────
COLOR_SKELETON = (0, 255, 200)       # Cyan-green
COLOR_KEYPOINT = (0, 220, 255)       # Yellow-orange
COLOR_BBOX = (255, 180, 0)           # Light blue
COLOR_BALL = (0, 255, 255)           # Yellow
COLOR_TRAJECTORY = (0, 200, 255)     # Orange-yellow
COLOR_TEXT_BG = (20, 20, 20)         # Dark background for text
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (0, 255, 100)
COLOR_RED = (0, 80, 255)
COLOR_ACCENT = (55, 255, 200)        # Tennis-ball green

# Shot type colors
SHOT_COLORS = {
    "forehand": (0, 220, 120),    # Green
    "backhand": (0, 165, 255),    # Orange
    "serve": (255, 200, 0),       # Cyan
    "volley": (0, 255, 255),      # Yellow
    "unknown": (180, 180, 180),   # Gray
}


def draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,
    confidence_threshold: float = 0.3,
    color: Tuple[int, int, int] = COLOR_SKELETON,
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw a skeleton overlay on the frame from COCO 17-keypoint format.
    keypoints: array of shape (17, 3) — [x, y, confidence] per keypoint.
    """
    # Draw bones (connections)
    for idx_a, idx_b in SKELETON_CONNECTIONS:
        if (keypoints[idx_a][2] >= confidence_threshold and
                keypoints[idx_b][2] >= confidence_threshold):
            pt_a = (int(keypoints[idx_a][0]), int(keypoints[idx_a][1]))
            pt_b = (int(keypoints[idx_b][0]), int(keypoints[idx_b][1]))
            cv2.line(frame, pt_a, pt_b, color, thickness, cv2.LINE_AA)

    # Draw keypoint dots
    for i, kp in enumerate(keypoints):
        if kp[2] >= confidence_threshold:
            center = (int(kp[0]), int(kp[1]))
            # Larger dots for major joints
            radius = 5 if i in (KP["left_shoulder"], KP["right_shoulder"],
                                KP["left_hip"], KP["right_hip"],
                                KP["left_knee"], KP["right_knee"]) else 3
            cv2.circle(frame, center, radius, COLOR_KEYPOINT, -1, cv2.LINE_AA)
            cv2.circle(frame, center, radius, (0, 0, 0), 1, cv2.LINE_AA)

    return frame


def draw_bbox(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    label: str = "",
    color: Tuple[int, int, int] = COLOR_BBOX,
    thickness: int = 2,
) -> np.ndarray:
    """Draw a bounding box with optional label."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

    if label:
        font_scale = 0.5
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
        cv2.putText(frame, label, (x1 + 4, y1 - 4), font, font_scale,
                    COLOR_WHITE, 1, cv2.LINE_AA)

    return frame


def draw_ball(
    frame: np.ndarray,
    position: Tuple[int, int],
    radius: int = 8,
) -> np.ndarray:
    """Draw a ball marker with glow effect."""
    x, y = int(position[0]), int(position[1])
    # Glow ring
    cv2.circle(frame, (x, y), radius + 4, (0, 180, 255), 2, cv2.LINE_AA)
    # Ball
    cv2.circle(frame, (x, y), radius, COLOR_BALL, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), radius, (0, 0, 0), 1, cv2.LINE_AA)
    return frame


def draw_trajectory(
    frame: np.ndarray,
    points: List[Tuple[int, int]],
    color: Tuple[int, int, int] = COLOR_TRAJECTORY,
    max_points: int = 30,
) -> np.ndarray:
    """Draw ball trajectory as a fading polyline."""
    if len(points) < 2:
        return frame

    recent = points[-max_points:]
    for i in range(1, len(recent)):
        alpha = i / len(recent)
        thickness = max(1, int(3 * alpha))
        fade_color = tuple(int(c * alpha) for c in color)
        pt1 = (int(recent[i - 1][0]), int(recent[i - 1][1]))
        pt2 = (int(recent[i][0]), int(recent[i][1]))
        cv2.line(frame, pt1, pt2, fade_color, thickness, cv2.LINE_AA)

    return frame


def draw_speed_badge(
    frame: np.ndarray,
    speed_kmh: float,
    position: Tuple[int, int],
    label: str = "",
) -> np.ndarray:
    """Draw a speed badge (e.g., '85 km/h') at the given position."""
    text = f"{speed_kmh:.0f} km/h"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, 2)

    x, y = int(position[0]), int(position[1])
    pad = 8

    # Badge background
    cv2.rectangle(frame,
                  (x - pad, y - th - pad * 2),
                  (x + tw + pad, y + pad),
                  COLOR_TEXT_BG, -1)
    cv2.rectangle(frame,
                  (x - pad, y - th - pad * 2),
                  (x + tw + pad, y + pad),
                  COLOR_ACCENT, 1, cv2.LINE_AA)

    # Speed text
    cv2.putText(frame, text, (x, y - 2), font, font_scale,
                COLOR_ACCENT, 2, cv2.LINE_AA)

    # Label above
    if label:
        lbl_scale = 0.45
        cv2.putText(frame, label, (x, y - th - pad - 2), font, lbl_scale,
                    COLOR_WHITE, 1, cv2.LINE_AA)

    return frame


def draw_shot_label(
    frame: np.ndarray,
    shot_type: str,
    confidence: float,
    position: Tuple[int, int],
) -> np.ndarray:
    """Draw a shot type label (e.g., 'Topspin Forehand')."""
    color = SHOT_COLORS.get(shot_type, SHOT_COLORS["unknown"])
    text = shot_type.capitalize()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.65
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, 2)

    x, y = int(position[0]), int(position[1])
    pad = 6

    cv2.rectangle(frame,
                  (x - pad, y - th - pad),
                  (x + tw + pad, y + pad),
                  COLOR_TEXT_BG, -1)
    cv2.rectangle(frame,
                  (x - pad, y - th - pad),
                  (x + tw + pad, y + pad),
                  color, 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, font_scale,
                color, 2, cv2.LINE_AA)

    return frame


def draw_frame_info(
    frame: np.ndarray,
    frame_num: int,
    total_frames: int,
    fps: float,
) -> np.ndarray:
    """Draw frame counter and FPS in the top-left corner."""
    text = f"{frame_num}/{total_frames}"
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Background pill
    (tw, th), _ = cv2.getTextSize(text, font, 0.55, 1)
    cv2.rectangle(frame, (8, 8), (20 + tw, 16 + th + 8), (0, 0, 0, 180), -1)
    cv2.putText(frame, text, (14, 14 + th), font, 0.55,
                COLOR_ACCENT, 1, cv2.LINE_AA)

    return frame


def annotate_frame(
    frame: np.ndarray,
    players: List[Dict[str, Any]],
    ball: Optional[Dict[str, Any]] = None,
    shot: Optional[Dict[str, Any]] = None,
    frame_num: int = 0,
    total_frames: int = 0,
    fps: float = 30.0,
) -> np.ndarray:
    """
    Master annotation function — draws all overlays on a single frame.
    """
    annotated = frame.copy()

    # Draw frame info
    if total_frames > 0:
        annotated = draw_frame_info(annotated, frame_num, total_frames, fps)

    # Draw each player
    for player in players:
        # Bounding box
        if "bbox" in player:
            label = f"Player {player.get('id', '?')}"
            annotate_color = COLOR_BBOX
            annotated = draw_bbox(annotated, player["bbox"], label, annotate_color)

        # Skeleton
        if "keypoints" in player and player["keypoints"] is not None:
            kps = np.array(player["keypoints"])
            if kps.shape[0] == 17:
                annotated = draw_skeleton(annotated, kps)

        # Speed badge near player
        if "speed_kmh" in player and player["speed_kmh"] > 0:
            bbox = player.get("bbox", (0, 0, 0, 0))
            badge_pos = (bbox[2] + 5, bbox[1] + 20)
            annotated = draw_speed_badge(
                annotated, player["speed_kmh"], badge_pos, "Player Speed"
            )

    # Draw ball
    if ball and "position" in ball and ball["position"] is not None:
        annotated = draw_ball(annotated, ball["position"])

        # Draw trajectory
        if "trajectory" in ball and ball["trajectory"]:
            annotated = draw_trajectory(annotated, ball["trajectory"])

        # Draw ball speed
        if "speed_kmh" in ball and ball["speed_kmh"] > 0:
            badge_pos = (ball["position"][0] + 15, ball["position"][1] - 15)
            annotated = draw_speed_badge(
                annotated, ball["speed_kmh"], badge_pos, "Ball Speed"
            )

    # Draw shot label
    if shot and shot.get("type") and shot["type"] != "unknown":
        h, w = annotated.shape[:2]
        annotated = draw_shot_label(
            annotated,
            shot["type"],
            shot.get("confidence", 0),
            (w - 220, 50),
        )

    return annotated
