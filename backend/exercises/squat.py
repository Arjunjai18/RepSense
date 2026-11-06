
import cv2
import mediapipe as mp
from collections import deque

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def calculate_angle(a, b, c):
    import math

    angle = math.degrees(
        math.atan2(c[1] - b[1], c[0] - b[0]) -
        math.atan2(a[1] - b[1], a[0] - b[0])
    )
    angle = abs(angle)
    return 360 - angle if angle > 180 else angle


class SquatDetector:

    def __init__(self):
        self.reps = 0
        self.stage = "STAND"
        self.angle = 0
        self.feedback = "Stand sideways to the camera"
        self.angle_history = deque(maxlen=5)

    def process(self, frame, landmarks, width, height):

        hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
        ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

        visibility = min(
            hip.visibility,
            knee.visibility,
            ankle.visibility
        )

        if visibility < 0.5:
            self.feedback = "Show your hip, knee and ankle"
            return frame

        hip_point = (int(hip.x * width), int(hip.y * height))
        knee_point = (int(knee.x * width), int(knee.y * height))
        ankle_point = (int(ankle.x * width), int(ankle.y * height))

        raw_angle = calculate_angle(
            hip_point, knee_point, ankle_point
        )

        self.angle_history.append(raw_angle)
        self.angle = sum(self.angle_history) / len(self.angle_history)

        if self.angle <= 95:
            self.stage = "DOWN"
            self.feedback = "Good! Now stand up"

        elif self.angle >= 160:
            if self.stage == "DOWN":
                self.reps += 1
            self.stage = "STAND"
            self.feedback = "Great! Keep going"

        else:
            self.feedback = "Keep moving"

        cv2.line(frame, hip_point, knee_point, (0, 255, 255), 3)
        cv2.line(frame, knee_point, ankle_point, (0, 255, 255), 3)
        cv2.circle(frame, knee_point, 8, (0, 0, 255), -1)

        return frame
