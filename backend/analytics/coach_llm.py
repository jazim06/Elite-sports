"""
AI Coach — Rule-based biomechanical analysis engine.
Generates specific, timestamped coaching notes based on actual joint angle data.
Each note identifies the specific flaw, explains why it matters, and suggests a drill.

When a GEMINI_API_KEY is set, also generates LLM-powered deep analysis.
"""
import os
import time

try:
    from google import genai
except ImportError:
    genai = None


# ── Biomechanical Reference Ranges (degrees) ────────────
# Based on sports science literature for tennis
REFERENCE = {
    "knee_right": {
        "optimal": (100, 145),
        "name": "Right Knee Flexion",
        "too_straight": {
            "threshold": 155,
            "flaw": "Standing too upright — insufficient knee bend",
            "impact": "Limits ground reaction force. You lose 15-25% of rotational power from the legs.",
            "drill": "Wall Sits with Racket Hold: Hold athletic stance (knees at 120°) against a wall for 30s × 4 sets. Shadow swing from this position.",
        },
        "too_bent": {
            "threshold": 85,
            "flaw": "Over-bending knees — sitting too low",
            "impact": "Delays explosive push-off and slows recovery movement between shots.",
            "drill": "Jump Squats: 3 sets of 8. Focus on explosive upward drive from a 120° knee position.",
        },
    },
    "elbow_right": {
        "optimal": (70, 140),
        "name": "Right Elbow Angle",
        "too_straight": {
            "threshold": 160,
            "flaw": "Arm too extended — 'pushing' the ball instead of whipping",
            "impact": "Straight arm contact kills racket head speed. The wrist can't snap through with a locked elbow.",
            "drill": "Towel Whip Drill: Hold a towel at the end, practice forehand motion focusing on elbow bending to 90° then snapping through.",
        },
        "too_bent": {
            "threshold": 50,
            "flaw": "Elbow tucked too tight — cramped swing",
            "impact": "Reduces swing arc and contact point consistency. Power drops significantly.",
            "drill": "Extended Reach Feeds: Partner feeds easy balls, focus on reaching OUT to the contact point with arm comfortably extended.",
        },
    },
    "shoulder_right": {
        "optimal": (25, 90),
        "name": "Right Shoulder Abduction",
        "too_straight": {
            "threshold": 130,
            "flaw": "Shoulder over-rotated — arm flying away from body",
            "impact": "Shoulder impingement risk increases. Control and accuracy suffer.",
            "drill": "Shadow Swings with Towel Under Arm: Tuck a towel under your hitting arm. If it falls, you're over-rotating.",
        },
        "too_bent": {
            "threshold": 15,
            "flaw": "Shoulder collapsed — arm pinned to body",
            "impact": "No separation between trunk and arm. Kinetic chain breaks down at the shoulder link.",
            "drill": "T-Spine Rotation Stretch: Lie on your side, rotate upper body open. 3 × 10 per side, then shadow serve.",
        },
    },
    "hip_right": {
        "optimal": (140, 175),
        "name": "Right Hip Extension",
        "too_straight": {
            "threshold": 178,
            "flaw": "Hips locked — no hip rotation loading",
            "impact": "The kinetic chain starts at the hips. Locked hips mean the trunk and arm must generate ALL the power alone.",
            "drill": "Medicine Ball Rotational Throws: Stand sideways to wall, rotate hips first, then throw. 3 × 10 each side.",
        },
        "too_bent": {
            "threshold": 120,
            "flaw": "Excessive forward lean from the hips",
            "impact": "Shifts weight too far forward, reducing balance and making recovery difficult.",
            "drill": "Balance Board Rallies: Stand on a balance board and shadow swing, focusing on maintaining upright posture.",
        },
    },
}


class AICoach:
    def __init__(self):
        """Initialize the AI Coach with rule-based analysis + optional LLM."""
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        if genai and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            print("🧠 AI Coach: Gemini API connected")
        else:
            print("🧠 AI Coach: Running rule-based analysis (set GEMINI_API_KEY for LLM mode)")

    def analyze_frame(self, frame_num: int, fps: float, kinematics_data: dict) -> list:
        """
        Analyze a single frame's kinematics and return a list of coaching notes.

        Each note is a dict:
        {
            "timestamp": "0:03",
            "frame": 90,
            "joint": "Right Knee",
            "severity": "warning" | "error" | "good",
            "flaw": "Standing too upright — insufficient knee bend",
            "angle": 162.3,
            "optimal_range": "100° – 145°",
            "impact": "...",
            "drill": "..."
        }
        """
        angles = kinematics_data.get("angles", {})
        if not angles:
            return []

        notes = []
        timestamp = self._frame_to_timestamp(frame_num, fps)

        for joint_key, angle in angles.items():
            if joint_key not in REFERENCE:
                continue

            ref = REFERENCE[joint_key]
            opt_min, opt_max = ref["optimal"]

            # Check if angle is outside optimal range
            if angle > ref["too_straight"]["threshold"]:
                notes.append({
                    "timestamp": timestamp,
                    "frame": frame_num,
                    "joint": ref["name"],
                    "severity": "error",
                    "flaw": ref["too_straight"]["flaw"],
                    "angle": round(angle, 1),
                    "optimal_range": f"{opt_min}° – {opt_max}°",
                    "impact": ref["too_straight"]["impact"],
                    "drill": ref["too_straight"]["drill"],
                })
            elif angle < ref["too_bent"]["threshold"]:
                notes.append({
                    "timestamp": timestamp,
                    "frame": frame_num,
                    "joint": ref["name"],
                    "severity": "error",
                    "flaw": ref["too_bent"]["flaw"],
                    "angle": round(angle, 1),
                    "optimal_range": f"{opt_min}° – {opt_max}°",
                    "impact": ref["too_bent"]["impact"],
                    "drill": ref["too_bent"]["drill"],
                })
            elif not (opt_min <= angle <= opt_max):
                # In the caution zone (between threshold and optimal)
                direction = "too_straight" if angle > opt_max else "too_bent"
                notes.append({
                    "timestamp": timestamp,
                    "frame": frame_num,
                    "joint": ref["name"],
                    "severity": "warning",
                    "flaw": ref[direction]["flaw"],
                    "angle": round(angle, 1),
                    "optimal_range": f"{opt_min}° – {opt_max}°",
                    "impact": ref[direction]["impact"],
                    "drill": ref[direction]["drill"],
                })

        return notes

    def _frame_to_timestamp(self, frame: int, fps: float) -> str:
        """Convert frame number to mm:ss.s timestamp."""
        fps = fps if fps and fps > 0 else 30.0
        total_seconds = frame / fps
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:04.1f}"
