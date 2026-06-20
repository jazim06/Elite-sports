import math
import numpy as np
from collections import deque
from scipy.signal import butter, filtfilt

from config import BIOMECH_THRESHOLDS, SMOOTHING


# filtfilt requires > padlen samples; for order=4, padlen = 3*(4+1)-1 = 14 → need ≥ 15
_FILTFILT_MIN_SAMPLES = 3 * (SMOOTHING["order"] + 1)


class KinematicsEngine:
    def __init__(self):
        self.angle_history = {
            "knee_left": deque(maxlen=5),
            "knee_right": deque(maxlen=5),
            "elbow_left": deque(maxlen=5),
            "elbow_right": deque(maxlen=5),
            "shoulder_left": deque(maxlen=5),
            "shoulder_right": deque(maxlen=5),
            "hip_left": deque(maxlen=5),
            "hip_right": deque(maxlen=5),
        }

        self.joint_definitions = [
            ("RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST", "elbow_right"),
            ("RIGHT_HIP", "RIGHT_SHOULDER", "RIGHT_ELBOW", "shoulder_right"),
            ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST", "elbow_left"),
            ("LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW", "shoulder_left"),
            ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE", "knee_right"),
            ("RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE", "hip_right"),
            ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE", "knee_left"),
            ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE", "hip_left"),
        ]

    def calculate_3d_angle(self, p1, p2, p3):
        """Angle at vertex p2 formed by p1-p2-p3, in degrees."""
        if not (p1 and p2 and p3):
            return 0.0
        v1 = np.array([p1["x"] - p2["x"], p1["y"] - p2["y"], p1.get("z", 0) - p2.get("z", 0)])
        v2 = np.array([p3["x"] - p2["x"], p3["y"] - p2["y"], p3.get("z", 0) - p2.get("z", 0)])
        m1, m2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if m1 == 0 or m2 == 0:
            return 0.0
        cos_a = np.clip(np.dot(v1, v2) / (m1 * m2), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_a)))

    def analyze_pose(self, landmarks_3d):
        """
        Per-frame: compute 8 joint angles.
        angular_velocity values here are deg/frame placeholders — they are
        replaced with proper deg/sec values by summarize_biomechanics().
        """
        if not landmarks_3d:
            return {}

        angles = {}
        VIS = 0.3

        for p1_name, vertex_name, p2_name, angle_name in self.joint_definitions:
            if all(k in landmarks_3d for k in [p1_name, vertex_name, p2_name]):
                p1 = landmarks_3d[p1_name]
                vertex = landmarks_3d[vertex_name]
                p2 = landmarks_3d[p2_name]
                if (p1.get("visibility", 1) >= VIS and
                        vertex.get("visibility", 1) >= VIS and
                        p2.get("visibility", 1) >= VIS):
                    angles[angle_name] = self.calculate_3d_angle(p1, vertex, p2)

        velocities = {}
        for joint, angle in angles.items():
            if joint in self.angle_history:
                history = self.angle_history[joint]
                if len(history) > 0:
                    velocities[f"{joint}_vel"] = angle - history[-1]
                history.append(angle)

        return {"angles": angles, "angular_velocities": velocities}


# ── Two-pass post-processor ────────────────────────────────────────────────

def summarize_biomechanics(frames_data: list, fps: float) -> dict:
    """
    Run once after the frame loop.  Reads landmarks_3d from every pose frame,
    smooths all time series, computes segment angular velocities in deg/sec,
    detects contact + phases, scores the kinematic sequence, and measures
    hip-shoulder separation.

    Side-effects:
      - Replaces each frame's angular_velocity dict with deg/sec values.
      - Adds segment_velocity {pelvis, trunk, arm, hand} in deg/sec to each frame.

    Returns a kinematic_sequence summary dict (top-level JSON field).
    Returns {"detected": False} when there are too few pose frames.
    """
    pose_frames = [
        f for f in frames_data
        if f.get("landmarks_3d") and f.get("joint_angles")
    ]
    T = len(pose_frames)
    if T < 5:
        return {"detected": False}

    timestamps = np.array([f["timestamp"] for f in pose_frames], dtype=float)
    # Guard against non-monotone timestamps (shouldn't happen, but be safe)
    if np.any(np.diff(timestamps) <= 0):
        timestamps = np.arange(T) / max(fps, 1.0)

    lm_list = [f["landmarks_3d"] for f in pose_frames]

    # ── Helper: extract a single coordinate ───────────────────────────────
    def _c(lm: dict, key: str, coord: str) -> float:
        pt = lm.get(key) or {}
        return pt.get(coord, 0.0)

    # ── Build joint-angle time series ─────────────────────────────────────
    angle_keys = [
        "knee_left", "knee_right", "elbow_left", "elbow_right",
        "shoulder_left", "shoulder_right", "hip_left", "hip_right",
    ]
    angle_series: dict[str, np.ndarray] = {}
    for key in angle_keys:
        raw = np.array(
            [f["joint_angles"].get(key, np.nan) if f.get("joint_angles") else np.nan
             for f in pose_frames]
        )
        nans = np.isnan(raw)
        if not nans.all():
            idxs = np.arange(T)
            raw[nans] = np.interp(idxs[nans], idxs[~nans], raw[~nans])
        else:
            raw = np.zeros(T)
        angle_series[key] = raw

    # ── Build segment orientation time series (transverse plane) ──────────
    # pelvis_angle = atan2(Δz, Δx) of right-hip → left-hip line
    pelvis_raw = np.array([
        math.atan2(
            _c(l, "RIGHT_HIP", "z") - _c(l, "LEFT_HIP", "z"),
            _c(l, "RIGHT_HIP", "x") - _c(l, "LEFT_HIP", "x"),
        ) for l in lm_list
    ])
    trunk_raw = np.array([
        math.atan2(
            _c(l, "RIGHT_SHOULDER", "z") - _c(l, "LEFT_SHOULDER", "z"),
            _c(l, "RIGHT_SHOULDER", "x") - _c(l, "LEFT_SHOULDER", "x"),
        ) for l in lm_list
    ])

    # ── Build arm/hand unit vectors (both sides) ──────────────────────────
    def _seg_vec(lm: dict, prox: str, dist: str) -> np.ndarray:
        v = np.array([
            _c(lm, dist, "x") - _c(lm, prox, "x"),
            _c(lm, dist, "y") - _c(lm, prox, "y"),
            _c(lm, dist, "z") - _c(lm, prox, "z"),
        ])
        n = np.linalg.norm(v)
        return v / n if n > 1e-6 else np.zeros(3)

    arm_r = np.array([_seg_vec(l, "RIGHT_SHOULDER", "RIGHT_ELBOW") for l in lm_list])
    arm_l = np.array([_seg_vec(l, "LEFT_SHOULDER",  "LEFT_ELBOW")  for l in lm_list])
    hand_r = np.array([_seg_vec(l, "RIGHT_ELBOW",   "RIGHT_WRIST") for l in lm_list])
    hand_l = np.array([_seg_vec(l, "LEFT_ELBOW",    "LEFT_WRIST")  for l in lm_list])

    # ── Smooth ────────────────────────────────────────────────────────────
    pelvis_s = _smooth(np.unwrap(pelvis_raw), fps)
    trunk_s  = _smooth(np.unwrap(trunk_raw),  fps)

    angle_s: dict[str, np.ndarray] = {k: _smooth(v, fps) for k, v in angle_series.items()}

    arm_s_r  = np.stack([_smooth(arm_r[:, i],  fps) for i in range(3)], axis=1)
    arm_s_l  = np.stack([_smooth(arm_l[:, i],  fps) for i in range(3)], axis=1)
    hand_s_r = np.stack([_smooth(hand_r[:, i], fps) for i in range(3)], axis=1)
    hand_s_l = np.stack([_smooth(hand_l[:, i], fps) for i in range(3)], axis=1)

    # ── Angular velocities in deg/sec ─────────────────────────────────────
    pelvis_vel = np.degrees(np.gradient(pelvis_s, timestamps))
    trunk_vel  = np.degrees(np.gradient(trunk_s,  timestamps))

    angle_vel: dict[str, np.ndarray] = {
        k: np.gradient(s, timestamps) for k, s in angle_s.items()
    }

    # For 3D unit vectors: angular speed = |du/dt| (rad/sec → deg/sec)
    def _angspeed(vecs: np.ndarray) -> np.ndarray:
        dvdt = np.gradient(vecs, timestamps, axis=0)
        return np.degrees(np.linalg.norm(dvdt, axis=1))

    arm_spd_r  = _angspeed(arm_s_r)
    arm_spd_l  = _angspeed(arm_s_l)
    hand_spd_r = _angspeed(hand_s_r)
    hand_spd_l = _angspeed(hand_s_l)

    # ── Dominant side ─────────────────────────────────────────────────────
    dominant = "RIGHT" if np.max(hand_spd_r) >= np.max(hand_spd_l) else "LEFT"
    arm_spd  = arm_spd_r  if dominant == "RIGHT" else arm_spd_l
    hand_spd = hand_spd_r if dominant == "RIGHT" else hand_spd_l

    # ── Contact frame + phases ────────────────────────────────────────────
    contact_idx = int(np.argmax(hand_spd))
    peak_hand   = float(hand_spd[contact_idx])
    threshold   = 0.25 * peak_hand

    accel_start = 0
    for i in range(contact_idx - 1, -1, -1):
        if hand_spd[i] < threshold:
            accel_start = i
            break

    followthrough_end = T - 1
    for i in range(contact_idx + 1, T):
        if hand_spd[i] < threshold:
            followthrough_end = i
            break

    phases = {
        "windup":        [pose_frames[0]["frame"],          pose_frames[accel_start]["frame"]],
        "acceleration":  [pose_frames[accel_start]["frame"], pose_frames[contact_idx]["frame"]],
        "contact":       pose_frames[contact_idx]["frame"],
        "follow_through":[pose_frames[contact_idx]["frame"], pose_frames[followthrough_end]["frame"]],
    }

    # ── Kinematic sequence ────────────────────────────────────────────────
    win = slice(accel_start, min(followthrough_end + 1, T))

    def _peak_idx(series: np.ndarray) -> int:
        sub = np.abs(series[win])
        return accel_start + int(np.argmax(sub)) if len(sub) else accel_start

    pi = _peak_idx(pelvis_vel)
    ti = _peak_idx(trunk_vel)
    ai = _peak_idx(arm_spd)
    hi = _peak_idx(hand_spd)

    segments = ["pelvis", "trunk", "arm", "hand"]
    peak_idx_map = {"pelvis": pi, "trunk": ti, "arm": ai, "hand": hi}
    peak_spd_map = {
        "pelvis": float(np.abs(pelvis_vel[pi])),
        "trunk":  float(np.abs(trunk_vel[ti])),
        "arm":    float(arm_spd[ai]),
        "hand":   float(hand_spd[hi]),
    }
    peak_time_map = {s: float(timestamps[peak_idx_map[s]]) for s in segments}

    order = sorted(segments, key=lambda s: peak_time_map[s])
    is_p2d = (order == segments)

    pairs = list(zip(segments, segments[1:]))
    thr = BIOMECH_THRESHOLDS
    n_order = sum(1 for a, b in pairs if peak_time_map[a] <= peak_time_map[b])
    n_mag   = sum(1 for a, b in pairs if peak_spd_map[b] > peak_spd_map[a])
    n_time  = sum(
        1 for a, b in pairs
        if thr["sequence_min_gap_sec"] <= abs(peak_time_map[b] - peak_time_map[a]) <= thr["sequence_max_gap_sec"]
    )
    sequence_score = round(100 * (0.4 * n_order / 3 + 0.3 * n_mag / 3 + 0.3 * n_time / 3))

    # ── Hip-shoulder separation ───────────────────────────────────────────
    sep_deg = np.degrees(trunk_s - pelvis_s)
    sep_peak_idx = int(np.argmax(np.abs(sep_deg)))

    # ── Write back per-frame velocities ──────────────────────────────────
    frame_to_idx = {f["frame"]: i for i, f in enumerate(pose_frames)}
    for fd in frames_data:
        fn = fd["frame"]
        if fn not in frame_to_idx:
            fd["angular_velocity"] = None
            fd["segment_velocity"]  = None
            continue
        i = frame_to_idx[fn]
        fd["angular_velocity"] = {
            f"{k}_vel": round(float(angle_vel[k][i]), 3) for k in angle_keys
        }
        fd["segment_velocity"] = {
            "pelvis": round(float(abs(pelvis_vel[i])), 2),
            "trunk":  round(float(abs(trunk_vel[i])),  2),
            "arm":    round(float(arm_spd[i]),          2),
            "hand":   round(float(hand_spd[i]),         2),
        }

    return {
        "detected":            True,
        "dominant_side":       dominant,
        "contact_frame":       pose_frames[contact_idx]["frame"],
        "contact_time":        round(float(timestamps[contact_idx]), 3),
        "phases":              phases,
        "peaks": {
            s: {
                "frame":             pose_frames[peak_idx_map[s]]["frame"],
                "time":              round(peak_time_map[s], 3),
                "speed_deg_per_sec": round(peak_spd_map[s], 1),
            }
            for s in segments
        },
        "order":                   order,
        "is_proximal_to_distal":   is_p2d,
        "sequence_score":          sequence_score,
        "hip_shoulder_separation": {
            "peak_deg":  round(float(sep_deg[sep_peak_idx]), 1),
            "peak_time": round(float(timestamps[sep_peak_idx]), 3),
        },
    }


def _smooth(series: np.ndarray, fps: float) -> np.ndarray:
    """Zero-lag Butterworth low-pass. Falls back to moving average for short clips."""
    n = len(series)
    if n < _FILTFILT_MIN_SAMPLES:
        w = min(3, n)
        if w <= 1:
            return series.copy()
        kernel = np.ones(w) / w
        padded = np.pad(series, w // 2, mode="edge")
        return np.convolve(padded, kernel, mode="valid")[:n]

    nyq = 0.5 * max(fps, 1.0)
    cutoff = min(SMOOTHING["cutoff_hz"] / nyq, 0.99)
    b, a = butter(SMOOTHING["order"], cutoff, btype="low")
    return filtfilt(b, a, series)
