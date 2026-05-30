import math
import numpy as np
from collections import deque

class KinematicsEngine:
    def __init__(self):
        """
        Engine for calculating 3D kinematics, joint angles, and velocities.
        """
        # Store recent frames' joint angles to calculate velocities
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
        
    def calculate_3d_angle(self, p1, p2, p3):
        """
        Calculate the 3D angle formed by 3 points (p1, p2, p3) with p2 as vertex.
        Args:
            p1, p2, p3: dicts with 'x', 'y', 'z' keys.
        Returns:
            Angle in degrees.
        """
        if not (p1 and p2 and p3):
            return 0.0
            
        # Create numpy arrays for vectors
        v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y'], p1['z'] - p2['z']])
        v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y'], p3['z'] - p2['z']])
        
        # Calculate magnitudes
        mag_v1 = np.linalg.norm(v1)
        mag_v2 = np.linalg.norm(v2)
        
        if mag_v1 == 0 or mag_v2 == 0:
            return 0.0
            
        # Calculate dot product
        dot_product = np.dot(v1, v2)
        
        # Calculate angle in radians and convert to degrees
        # Clip to [-1.0, 1.0] to avoid precision errors causing nan
        cos_angle = np.clip(dot_product / (mag_v1 * mag_v2), -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        
        return float(np.degrees(angle_rad))

    def analyze_pose(self, landmarks_3d):
        """
        Analyze the 3D pose to calculate critical joint angles and kinematic sequence.
        Args:
            landmarks_3d: Dictionary of MediaPipe landmarks (keys are string names)
        Returns:
            Dict containing calculated angles, velocities, and phase information.
        """
        if not landmarks_3d:
            return {}

        angles = {}
        
        # Right Arm Kinematics
        if all(k in landmarks_3d for k in ['RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST']):
            angles["elbow_right"] = self.calculate_3d_angle(
                landmarks_3d['RIGHT_SHOULDER'],
                landmarks_3d['RIGHT_ELBOW'],
                landmarks_3d['RIGHT_WRIST']
            )
            
        if all(k in landmarks_3d for k in ['RIGHT_HIP', 'RIGHT_SHOULDER', 'RIGHT_ELBOW']):
            angles["shoulder_right"] = self.calculate_3d_angle(
                landmarks_3d['RIGHT_HIP'],
                landmarks_3d['RIGHT_SHOULDER'],
                landmarks_3d['RIGHT_ELBOW']
            )

        # Right Leg Kinematics
        if all(k in landmarks_3d for k in ['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE']):
            angles["knee_right"] = self.calculate_3d_angle(
                landmarks_3d['RIGHT_HIP'],
                landmarks_3d['RIGHT_KNEE'],
                landmarks_3d['RIGHT_ANKLE']
            )

        # Trunk/Hip Kinematics (Trunk Lean)
        if all(k in landmarks_3d for k in ['RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE']):
            angles["hip_right"] = self.calculate_3d_angle(
                landmarks_3d['RIGHT_SHOULDER'],
                landmarks_3d['RIGHT_HIP'],
                landmarks_3d['RIGHT_KNEE']
            )
            
        # Update history and calculate angular velocities
        velocities = {}
        for joint, angle in angles.items():
            if joint in self.angle_history:
                history = self.angle_history[joint]
                
                # If we have previous frames, calculate rate of change (deg/frame)
                if len(history) > 0:
                    prev_angle = history[-1]
                    velocity = angle - prev_angle
                    velocities[f"{joint}_vel"] = velocity
                    
                history.append(angle)

        return {
            "angles": angles,
            "angular_velocities": velocities
        }
