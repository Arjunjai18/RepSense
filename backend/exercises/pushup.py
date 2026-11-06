
import cv2
import mediapipe as mp
from collections import deque
from .squat import calculate_angle

mp_pose = mp.solutions.pose


class PushupDetector:

    def __init__(self):
        self.reps = 0
        self.stage = "UP"
        self.angle = 0
        self.feedback = "Position yourself sideways to the camera"
        self.angle_history = deque(maxlen=5)

    def process(self, frame, landmarks, width, height):

        shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
        hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

        visibility = min(
            shoulder.visibility,
            elbow.visibility,
            wrist.visibility,
            hip.visibility,
            ankle.visibility
        )

        if visibility < 0.5:
            self.feedback = "Show your full body from the side"
            return frame

        shoulder_point = (
            int(shoulder.x * width),
            int(shoulder.y * height)
        )

        elbow_point = (
            int(elbow.x * width),
            int(elbow.y * height)
        )

        wrist_point = (
            int(wrist.x * width),
            int(wrist.y * height)
        )

        hip_point = (
            int(hip.x * width),
            int(hip.y * height)
        )

        ankle_point = (
            int(ankle.x * width),
            int(ankle.y * height)
        )

        raw_angle = calculate_angle(
            shoulder_point,
            elbow_point,
            wrist_point
        )

        self.angle_history.append(raw_angle)
        self.angle = sum(self.angle_history) / len(self.angle_history)

        # Elbow movement rep detection
        if self.angle <= 90:
            self.stage = "DOWN"
            self.feedback = "Good depth! Push yourself up"

        elif self.angle >= 150:
            if self.stage == "DOWN":
                self.reps += 1

            self.stage = "UP"
            self.feedback = "Great! Maintain your body alignment"

        else:
            self.feedback = "Keep moving steadily"

        # Approximate shoulder-hip-ankle body alignment
        alignment_angle = calculate_angle(
            shoulder_point,
            hip_point,
            ankle_point
        )

        if alignment_angle < 150:
            self.feedback = "Keep your body straight"

        cv2.line(frame, shoulder_point, elbow_point, (0, 255, 255), 3)
        cv2.line(frame, elbow_point, wrist_point, (0, 255, 255), 3)
        cv2.line(frame, shoulder_point, hip_point, (80, 230, 100), 2)
        cv2.line(frame, hip_point, ankle_point, (80, 230, 100), 2)

        return frame
