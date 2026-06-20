"""
AI Coaching Rules Engine — post-loop, phase-aware and sequence-aware.

analyze() replaces the old per-frame analyze_frame() call. It is invoked once
after summarize_biomechanics() has identified contact, phases, and the
kinematic sequence.  Notes are evaluated at the biomechanically meaningful
phase for each joint (knee at loading, elbow at contact) so the feedback is
not confused by mid-swing positions.
"""
from typing import Any
from config import BIOMECH_THRESHOLDS


class AICoach:
    def analyze(
        self,
        frames_data: list,
        sequence: dict,
        fps: float,
    ) -> list[dict[str, Any]]:
        """
        Generate coaching notes from the post-loop kinematic summary.
        Returns a list of notes in the same schema as the old analyze_frame().
        """
        notes: list[dict] = []

        if not sequence.get("detected"):
            return notes

        phases    = sequence["phases"]
        dominant  = sequence.get("dominant_side", "RIGHT").lower()
        contact_f = sequence["contact_frame"]

        # ── Loading frame = end of windup ─────────────────────────────────
        loading_frame_num = phases["windup"][1]
        loading_fd = _nearest_frame(frames_data, loading_frame_num)
        contact_fd = _nearest_frame(frames_data, contact_f)

        thr = BIOMECH_THRESHOLDS

        # ── Knee bend at loading ──────────────────────────────────────────
        for side in (dominant, _other(dominant)):
            knee_key = f"knee_{side}"
            if loading_fd and loading_fd.get("joint_angles"):
                angle = loading_fd["joint_angles"].get(knee_key)
                if angle is not None:
                    ts = _fmt(loading_frame_num, fps)
                    if angle < thr["knee_bend_loading_min"]:
                        notes.append(_note(
                            ts, loading_frame_num, knee_key, "error",
                            "Knees bent too deep at loading — you lose explosive power and react slower.",
                            angle,
                            [thr["knee_bend_loading_min"], thr["knee_bend_loading_max"]],
                            "Reduces ground-reaction force transfer and split-step speed",
                            "Shadow swings with a medicine ball to feel the leg drive.",
                        ))
                    elif angle > thr["knee_bend_loading_max"]:
                        notes.append(_note(
                            ts, loading_frame_num, knee_key, "warning",
                            "Knees too straight at loading — bend them to load power from the ground.",
                            angle,
                            [thr["knee_bend_loading_min"], thr["knee_bend_loading_max"]],
                            "Reduces ground-reaction force and kinetic-chain energy",
                            "Shadow swings with a medicine ball to feel the leg drive.",
                        ))

        # ── Elbow extension at contact ────────────────────────────────────
        for side in (dominant, _other(dominant)):
            elbow_key = f"elbow_{side}"
            if contact_fd and contact_fd.get("joint_angles"):
                angle = contact_fd["joint_angles"].get(elbow_key)
                if angle is not None:
                    ts = _fmt(contact_f, fps)
                    if angle < thr["elbow_extension_contact_min"]:
                        notes.append(_note(
                            ts, contact_f, elbow_key, "error",
                            "Elbow too bent at contact — you lose reach and racket speed.",
                            angle,
                            [thr["elbow_extension_contact_min"], thr["elbow_extension_contact_max"]],
                            "Reduces reach, power, and consistency",
                            "Practice hitting with a straight-arm contact point against a wall.",
                        ))
                    elif angle > thr["elbow_extension_contact_max"]:
                        notes.append(_note(
                            ts, contact_f, elbow_key, "warning",
                            "Arm is hyper-extended at contact — high risk of tennis elbow.",
                            angle,
                            [thr["elbow_extension_contact_min"], thr["elbow_extension_contact_max"]],
                            "Increases lateral-epicondyle loading and injury risk",
                            "Practice hitting with a straight-arm contact point against a wall.",
                        ))

        # ── Kinematic sequence order ──────────────────────────────────────
        if not sequence.get("is_proximal_to_distal", True):
            ts = _fmt(contact_f, fps)
            notes.append(_note(
                ts, contact_f, "kinematic_sequence", "error",
                "Shoulder fired before hips — power leak from the ground up. "
                "Hips must rotate first, then torso, then arm, then hand.",
                0.0, [0.0, 0.0],
                "Breaks the kinetic chain; power generated by the legs is not summated into the racket",
                "Towel drill: hold a towel between your knees, rotate hips before swinging the arm.",
            ))

        # ── Hip-shoulder separation (X-factor) ────────────────────────────
        sep = sequence.get("hip_shoulder_separation", {})
        if sep:
            peak = abs(sep.get("peak_deg", 0.0))
            min_sep = thr["hip_shoulder_separation_min"]
            if peak < min_sep:
                ts = _fmt(contact_f, fps)
                notes.append(_note(
                    ts, contact_f, "hip_shoulder_separation", "warning",
                    f"Hip-shoulder separation is only {peak:.0f}° (target ≥ {min_sep:.0f}°) — "
                    "insufficient X-factor reduces stored rotational energy.",
                    peak, [min_sep, 60.0],
                    "Less elastic energy stored in the trunk musculature means lower racket speed",
                    "Rotation shadow drill: exaggerate hip turn before shoulder turn.",
                ))

        return notes

    # Legacy per-frame shim — kept so old call sites don't crash during transition.
    def analyze_frame(self, _frame_num: int, _fps: float, _kinematics_data: dict) -> list:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────

def _other(side: str) -> str:
    return "left" if side == "right" else "right"


def _nearest_frame(frames_data: list, target: int) -> dict | None:
    if not frames_data:
        return None
    return min(frames_data, key=lambda f: abs(f["frame"] - target))


def _fmt(frame: int, fps: float) -> str:
    secs = frame / max(fps, 1)
    mins = int(secs // 60)
    return f"{mins}:{secs % 60:04.1f}"


def _note(
    timestamp: str,
    frame: int,
    joint: str,
    severity: str,
    flaw: str,
    actual_angle: float,
    optimal_range: list,
    impact: str,
    drill: str,
) -> dict:
    return {
        "timestamp":    timestamp,
        "frame":        frame,
        "joint":        joint,
        "severity":     severity,
        "flaw":         flaw,
        "actual_angle": round(actual_angle, 1),
        "optimal_range": optimal_range,
        "impact":       impact,
        "drill":        drill,
    }
