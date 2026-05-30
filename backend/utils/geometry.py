"""
Geometry utilities for coordinate transforms, angle calculations, and court mapping.
"""
import numpy as np
from typing import Tuple, Optional, List


def angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Calculate the angle in degrees between two 2D or 3D vectors.
    Returns angle in range [0, 180].
    """
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def joint_angle(
    point_a: np.ndarray,
    point_b: np.ndarray,  # the joint vertex
    point_c: np.ndarray,
) -> float:
    """
    Calculate the angle at point_b formed by segments BA and BC.
    point_a, point_b, point_c are (x, y) or (x, y, z) arrays.
    Returns angle in degrees [0, 180].
    """
    v1 = point_a - point_b
    v2 = point_c - point_b
    return angle_between_vectors(v1, v2)


def euclidean_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """Euclidean distance between two points."""
    return float(np.linalg.norm(p1 - p2))


def midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Midpoint between two points."""
    return (p1 + p2) / 2.0


def pixel_speed_to_real(
    pixel_displacement: float,
    homography: Optional[np.ndarray],
    fps: float,
    scale_factor: float = 1.0,
) -> float:
    """
    Convert pixel displacement per frame to real-world speed (km/h).
    If no homography is available, uses a rough scale_factor (pixels per meter).
    """
    if fps <= 0:
        return 0.0

    if homography is not None:
        # Use homography scale (average of x and y scaling)
        sx = np.linalg.norm(homography[:2, 0])
        sy = np.linalg.norm(homography[:2, 1])
        avg_scale = (sx + sy) / 2.0
        meters_per_pixel = 1.0 / (avg_scale + 1e-8)
    else:
        meters_per_pixel = 1.0 / (scale_factor + 1e-8)

    meters_per_frame = pixel_displacement * meters_per_pixel
    meters_per_second = meters_per_frame * fps
    kmh = meters_per_second * 3.6
    return round(kmh, 1)


def transform_point(
    point: Tuple[float, float],
    homography: np.ndarray,
) -> Tuple[float, float]:
    """
    Transform a 2D point using a homography matrix.
    Returns the transformed (x, y) coordinates.
    """
    pt = np.array([point[0], point[1], 1.0])
    transformed = homography @ pt
    transformed /= transformed[2] + 1e-8
    return (float(transformed[0]), float(transformed[1]))


def points_to_court_coords(
    points: List[Tuple[float, float]],
    homography: np.ndarray,
) -> List[Tuple[float, float]]:
    """Transform a list of pixel points to court coordinates."""
    return [transform_point(p, homography) for p in points]


def estimate_scale_from_court(
    court_pixel_width: float,
    real_width: float = 10.97,
) -> float:
    """
    Estimate a rough pixels-per-meter scale from visible court width.
    Fallback when homography isn't available.
    """
    if court_pixel_width <= 0:
        return 50.0  # rough default
    return court_pixel_width / real_width
