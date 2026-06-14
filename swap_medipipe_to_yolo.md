# Switch Pose Model: MediaPipe → YOLOv8m-Pose

## Changes Required

### Backend

#### [MODIFY] pose_3d.py → Rewrite to use YOLOv8-Pose
- Load `yolov8m-pose.pt` via Ultralytics API
- Return normalized 2D keypoints (COCO 17-keypoint format) + confidence
- Map COCO keypoint indices to named joints for compatibility

#### [MODIFY] analyzer.py → Adapt to new pose output format
- Process at higher resolution (1080px instead of 720px since YOLO handles it well)
- Process every frame (YOLO is faster than MediaPipe at this)
- Adapt landmark access to new key names

#### [MODIFY] kinematics.py → Map COCO names to angle calculations
- COCO uses different joint names (e.g., `right_shoulder` instead of `RIGHT_SHOULDER`)
- Same angle math, just different key names

### Frontend

#### [MODIFY] VideoCanvas.tsx → Update skeleton connections for COCO 17
- COCO has 17 keypoints (vs MediaPipe's 33)
- Different connection topology (simpler, more reliable)

## COCO 17 Keypoints
0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear,
5: left_shoulder, 6: right_shoulder, 7: left_elbow, 8: right_elbow,
9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip,
13: left_knee, 14: right_knee, 15: left_ankle, 16: right_ankle
