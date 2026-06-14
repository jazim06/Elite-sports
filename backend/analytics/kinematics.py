import math
import numpy as np
from collections import deque

class KinematicsEngine:
    def __init__(self):
        """
        Engine for calculating joint angles and angular velocities.
        Works with both MediaPipe and COCO (YOLOv8-Pose) keypoint formats.
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

        # Joint angle definitions: (point_a, vertex, point_b) → angle name
        # Using uppercase COCO names (compatible with both MediaPipe and our YOLO output)
        self.joint_definitions = [
            # Right Arm
            ("RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST", "elbow_right"),
            ("RIGHT_HIP", "RIGHT_SHOULDER", "RIGHT_ELBOW", "shoulder_right"),
            # Left Arm
            ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST", "elbow_left"),
            ("LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW", "shoulder_left"),
            # Right Leg
            ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE", "knee_right"),
            ("RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE", "hip_right"),
            # Left Leg
            ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE", "knee_left"),
            ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE", "hip_left"),
        ]
        
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
        v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y'], p1.get('z', 0) - p2.get('z', 0)])
        v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y'], p3.get('z', 0) - p2.get('z', 0)])
        
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
        Analyze the pose to calculate critical joint angles and kinematic sequence.
        
        Works with any keypoint format (MediaPipe or COCO) as long as the
        landmark names use uppercase format (e.g., RIGHT_SHOULDER).
        
        Args:
            landmarks_3d: Dictionary of landmarks (keys are uppercase string names)
        Returns:
            Dict containing calculated angles, velocities, and phase information.
        """
        if not landmarks_3d:
            return {}

        angles = {}
        VISIBILITY_THRESHOLD = 0.3  # Skip low-confidence keypoints

        for p1_name, vertex_name, p2_name, angle_name in self.joint_definitions:
            if all(k in landmarks_3d for k in [p1_name, vertex_name, p2_name]):
                # Check visibility/confidence for all three points
                p1 = landmarks_3d[p1_name]
                vertex = landmarks_3d[vertex_name]
                p2 = landmarks_3d[p2_name]
                
                if (p1.get('visibility', 1) >= VISIBILITY_THRESHOLD and
                    vertex.get('visibility', 1) >= VISIBILITY_THRESHOLD and
                    p2.get('visibility', 1) >= VISIBILITY_THRESHOLD):
                    angles[angle_name] = self.calculate_3d_angle(p1, vertex, p2)
            
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

