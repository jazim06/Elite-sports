import cv2
import mediapipe as mp
import numpy as np
import ssl
import urllib.request

# Workaround for macOS Python SSL certificate verify failed error during MediaPipe model download
ssl._create_default_https_context = ssl._create_unverified_context

class Pose3DEstimator:
    def __init__(self):
        """Initialize MediaPipe Pose model for 3D landmarks."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1, # 0=fast, 1=balanced, 2=heavy. Using 1 for speed+accuracy balance
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def process_frame(self, frame_bgr):
        """
        Process a single frame and extract 3D pose.
        
        Args:
            frame_bgr: OpenCV image (BGR)
            
        Returns:
            dict with 'landmarks_3d', 'landmarks_2d', 'annotated_frame'
            or None if no pose detected.
        """
        # Convert the BGR image to RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # Process the image and find poses
        results = self.pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
            
        # Extract 3D landmarks (x, y, z)
        # z is the landmark depth with the origin at the center of the hips
        # x and y are normalized to [0.0, 1.0] by image width and height
        # visibility is [0.0, 1.0] indicating likelihood of landmark being visible
        
        landmarks_3d = {}
        landmarks_2d = {}
        h, w, _ = frame_bgr.shape
        
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            name = self.mp_pose.PoseLandmark(idx).name
            
            # 3D relative coords
            landmarks_3d[name] = {
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z,
                "visibility": landmark.visibility
            }
            
            # 2D pixel coords
            landmarks_2d[name] = {
                "x": int(landmark.x * w),
                "y": int(landmark.y * h)
            }

        # Draw the pose annotation on the image.
        annotated_frame = frame_bgr.copy()
        self.mp_drawing.draw_landmarks(
            annotated_frame,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style())
            
        return {
            "landmarks_3d": landmarks_3d,
            "landmarks_2d": landmarks_2d,
            "annotated_frame": annotated_frame
        }
