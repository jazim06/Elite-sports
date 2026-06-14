"""
AI Coaching Rules Engine — Generates biomechanical notes based on joint angles.
"""
from typing import Dict, List, Any

class AICoach:
    def __init__(self):
        # Define optimal ranges for tennis mechanics
        self.rules = {
            "knee_bend": {
                "joint": "knee_right", # Assuming right-handed for now
                "min": 110.0,
                "max": 140.0,
                "flaw_low": "Knees bent too deep. You will lose explosive power and react slower.",
                "flaw_high": "Knees are too straight. Bend them to load power from the ground.",
                "drill": "Shadow swings with a medicine ball to feel the leg drive."
            },
            "elbow_extension": {
                "joint": "elbow_right",
                "min": 160.0,
                "max": 180.0,
                "flaw_low": "Elbow is too bent at contact. You are losing reach and racket speed.",
                "flaw_high": "Arm is hyper-extended. High risk of tennis elbow.",
                "drill": "Practice hitting with a straight arm contact point against a wall."
            }
        }

    def analyze_frame(self, frame_num: int, fps: float, kinematics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check joint angles against optimal ranges and generate coaching notes.
        """
        notes = []
        angles = kinematics_data.get("angles", {})
        
        if not angles:
            return notes
            
        timestamp = self._format_time(frame_num, fps)

        for rule_name, rule in self.rules.items():
            joint_name = rule["joint"]
            if joint_name in angles:
                angle = angles[joint_name]
                
                if angle < rule["min"]:
                    notes.append({
                        "timestamp": timestamp,
                        "frame": frame_num,
                        "joint": joint_name,
                        "severity": "error",
                        "flaw": rule["flaw_low"],
                        "actual_angle": angle,
                        "optimal_range": [rule["min"], rule["max"]],
                        "impact": "Reduces power and consistency",
                        "drill": rule["drill"]
                    })
                elif angle > rule["max"]:
                    notes.append({
                        "timestamp": timestamp,
                        "frame": frame_num,
                        "joint": joint_name,
                        "severity": "warning",
                        "flaw": rule["flaw_high"],
                        "actual_angle": angle,
                        "optimal_range": [rule["min"], rule["max"]],
                        "impact": "Increases injury risk",
                        "drill": rule["drill"]
                    })

        return notes

    def _format_time(self, frame: int, fps: float) -> str:
        secs = frame / max(fps, 1)
        mins = int(secs // 60)
        rem = secs % 60
        return f"{mins}:{rem:04.1f}"
