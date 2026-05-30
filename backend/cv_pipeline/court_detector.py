"""
Court Detector — Detects tennis court lines using OpenCV and computes
a homography matrix to map camera view → top-down court coordinates.
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List
from config import COURT_LENGTH, COURT_WIDTH, SINGLES_WIDTH, SERVICE_LINE_DIST


# Standard tennis court keypoints in real-world coordinates (meters)
# Origin at top-left corner of the doubles court
COURT_REFERENCE_POINTS = np.array([
    [0, 0],                                       # Top-left doubles
    [COURT_WIDTH, 0],                              # Top-right doubles
    [COURT_WIDTH, COURT_LENGTH],                   # Bottom-right doubles
    [0, COURT_LENGTH],                             # Bottom-left doubles
    [(COURT_WIDTH - SINGLES_WIDTH) / 2, 0],        # Top-left singles
    [(COURT_WIDTH + SINGLES_WIDTH) / 2, 0],        # Top-right singles
    [(COURT_WIDTH - SINGLES_WIDTH) / 2, COURT_LENGTH],  # Bottom-left singles
    [(COURT_WIDTH + SINGLES_WIDTH) / 2, COURT_LENGTH],  # Bottom-right singles
    [0, COURT_LENGTH / 2],                         # Net left
    [COURT_WIDTH, COURT_LENGTH / 2],               # Net right
    [COURT_WIDTH / 2, COURT_LENGTH / 2 - SERVICE_LINE_DIST],  # Center T top
    [COURT_WIDTH / 2, COURT_LENGTH / 2 + SERVICE_LINE_DIST],  # Center T bottom
], dtype=np.float32)


class CourtDetector:
    """
    Detects tennis court lines from a video frame using classical CV:
    1. White pixel extraction → 2. Hough Line Transform → 3. Intersection finding
    → 4. Homography estimation to a reference court model.
    """

    def __init__(self):
        self.homography: Optional[np.ndarray] = None
        self.inv_homography: Optional[np.ndarray] = None
        self._court_corners_px: Optional[np.ndarray] = None
        self._calibrated = False

    def detect(self, frame: np.ndarray) -> bool:
        """
        Attempt to detect court lines and compute homography.
        Returns True if successful.
        """
        # Extract white lines from the frame
        white_mask = self._extract_white_lines(frame)

        # Detect lines using Hough transform
        lines = self._detect_lines(white_mask)
        if lines is None or len(lines) < 4:
            return False

        # Classify lines into horizontal and vertical
        h_lines, v_lines = self._classify_lines(lines, frame.shape)

        if len(h_lines) < 2 or len(v_lines) < 2:
            return False

        # Find intersections → court corner candidates
        intersections = self._find_intersections(h_lines, v_lines, frame.shape)

        if len(intersections) < 4:
            return False

        # Select the 4 best corner points (outermost)
        corners = self._select_court_corners(intersections, frame.shape)

        if corners is None:
            return False

        # Compute homography
        src_points = corners.astype(np.float32)
        dst_points = COURT_REFERENCE_POINTS[:4].astype(np.float32)

        H, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)

        if H is not None:
            self.homography = H
            self.inv_homography = np.linalg.inv(H)
            self._court_corners_px = corners
            self._calibrated = True
            return True

        return False

    def pixel_to_court(self, px: float, py: float) -> Optional[Tuple[float, float]]:
        """Transform pixel coordinates to court coordinates (meters)."""
        if self.homography is None:
            return None
        pt = np.array([px, py, 1.0])
        transformed = self.homography @ pt
        transformed /= transformed[2] + 1e-8
        return (float(transformed[0]), float(transformed[1]))

    def court_to_pixel(self, cx: float, cy: float) -> Optional[Tuple[float, float]]:
        """Transform court coordinates (meters) to pixel coordinates."""
        if self.inv_homography is None:
            return None
        pt = np.array([cx, cy, 1.0])
        transformed = self.inv_homography @ pt
        transformed /= transformed[2] + 1e-8
        return (float(transformed[0]), float(transformed[1]))

    def get_scale_factor(self) -> float:
        """
        Estimate pixels-per-meter from the homography.
        Used as a fallback for speed calculations.
        """
        if self._court_corners_px is not None:
            # Measure pixel width between corners
            width_px = np.linalg.norm(
                self._court_corners_px[1] - self._court_corners_px[0]
            )
            return float(width_px / COURT_WIDTH)
        return 50.0  # rough default

    def draw_court_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw detected court lines overlay on the frame."""
        if self._court_corners_px is None:
            return frame

        overlay = frame.copy()
        corners = self._court_corners_px.astype(int)

        # Draw court boundary
        for i in range(4):
            pt1 = tuple(corners[i])
            pt2 = tuple(corners[(i + 1) % 4])
            cv2.line(overlay, pt1, pt2, (0, 255, 0), 2, cv2.LINE_AA)

        # Draw center line (approximate)
        mid_top = ((corners[0] + corners[1]) / 2).astype(int)
        mid_bot = ((corners[3] + corners[2]) / 2).astype(int)
        cv2.line(overlay, tuple(mid_top), tuple(mid_bot), (0, 255, 0), 1, cv2.LINE_AA)

        # Blend
        return cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def reset(self):
        """Reset calibration."""
        self.homography = None
        self.inv_homography = None
        self._court_corners_px = None
        self._calibrated = False

    # ── Private methods ────────────────────────────────

    def _extract_white_lines(self, frame: np.ndarray) -> np.ndarray:
        """Extract white/bright pixels that likely correspond to court lines."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Adaptive threshold to handle varying lighting
        # Also try high-value threshold for white lines
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # Also check in HSV for white (low saturation, high value)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 50, 255]))

        # Combine both masks
        combined = cv2.bitwise_or(binary, white_mask)

        # Cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)

        return combined

    def _detect_lines(self, mask: np.ndarray) -> Optional[np.ndarray]:
        """Detect lines using probabilistic Hough transform."""
        edges = cv2.Canny(mask, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=50,
            maxLineGap=30,
        )
        return lines

    def _classify_lines(
        self,
        lines: np.ndarray,
        frame_shape: Tuple,
    ) -> Tuple[List, List]:
        """
        Classify detected lines into roughly horizontal and vertical.
        Uses angle relative to horizontal.
        """
        h_lines = []
        v_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(abs(y2 - y1), abs(x2 - x1) + 1e-8))

            if angle < 30:
                h_lines.append((x1, y1, x2, y2))
            elif angle > 60:
                v_lines.append((x1, y1, x2, y2))

        return h_lines, v_lines

    def _find_intersections(
        self,
        h_lines: List,
        v_lines: List,
        frame_shape: Tuple,
    ) -> List[Tuple[float, float]]:
        """Find intersection points between horizontal and vertical lines."""
        intersections = []
        h, w = frame_shape[:2]

        for hl in h_lines:
            for vl in v_lines:
                pt = self._line_intersection(hl, vl)
                if pt is not None:
                    x, y = pt
                    # Keep only points within frame bounds (with margin)
                    margin = 50
                    if -margin <= x <= w + margin and -margin <= y <= h + margin:
                        intersections.append(pt)

        return intersections

    @staticmethod
    def _line_intersection(
        line1: Tuple,
        line2: Tuple,
    ) -> Optional[Tuple[float, float]]:
        """Find intersection of two line segments (extended to infinity)."""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-6:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)

        return (float(ix), float(iy))

    def _select_court_corners(
        self,
        intersections: List[Tuple[float, float]],
        frame_shape: Tuple,
    ) -> Optional[np.ndarray]:
        """
        Select 4 corner points from intersection candidates.
        Uses convex hull and picks the 4 most extreme points.
        """
        if len(intersections) < 4:
            return None

        points = np.array(intersections, dtype=np.float32)

        # Use convex hull
        try:
            hull = cv2.convexHull(points.reshape(-1, 1, 2))
            hull_points = hull.reshape(-1, 2)
        except cv2.error:
            return None

        if len(hull_points) < 4:
            return None

        # Pick 4 extreme points (top-left, top-right, bottom-right, bottom-left)
        h, w = frame_shape[:2]
        center = np.array([w / 2, h / 2])

        # Sort by angle from center
        angles = np.arctan2(hull_points[:, 1] - center[1],
                            hull_points[:, 0] - center[0])
        sorted_idx = np.argsort(angles)
        sorted_points = hull_points[sorted_idx]

        # Take 4 evenly spaced points
        n = len(sorted_points)
        if n >= 4:
            indices = [int(i * n / 4) for i in range(4)]
            corners = sorted_points[indices]

            # Order: top-left, top-right, bottom-right, bottom-left
            corners = self._order_corners(corners)
            return corners

        return None

    @staticmethod
    def _order_corners(corners: np.ndarray) -> np.ndarray:
        """Order 4 corners as: top-left, top-right, bottom-right, bottom-left."""
        # Sort by y-coordinate
        sorted_by_y = corners[np.argsort(corners[:, 1])]
        top = sorted_by_y[:2]
        bottom = sorted_by_y[2:]

        # Sort top by x
        top = top[np.argsort(top[:, 0])]
        # Sort bottom by x (reverse for bottom-right first)
        bottom = bottom[np.argsort(bottom[:, 0])[::-1]]

        return np.array([top[0], top[1], bottom[0], bottom[1]])
