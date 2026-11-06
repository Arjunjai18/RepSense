
import cv2
import mediapipe as mp
from collections import deque
from .squat import calculate_angle

mp_pose = mp.solutions.pose


class BicepCurlDetector:

    def __init__(self):
        self.reps = 0
        self.stage = "DOWN"
        self.angle = 0
        self.feedback = "Keep your upper arm close to your body"
        self.angle_history = deque(maxlen=5)

    def process(self, frame, landmarks, width, height):

        shoulder = landmarks[
            mp_pose.PoseLandmark.LEFT_SHOULDER.value
        ]

        elbow = landmarks[
            mp_pose.PoseLandmark.LEFT_ELBOW.value
        ]

        wrist = landmarks[
            mp_pose.PoseLandmark.LEFT_WRIST.value
        ]

        visibility = min(
            shoulder.visibility,
            elbow.visibility,
            wrist.visibility
        )

        if visibility < 0.5:
            self.feedback = "Keep your arm visible to the camera"
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

        raw_angle = calculate_angle(
            shoulder_point,
            elbow_point,
            wrist_point
        )

        self.angle_history.append(raw_angle)

        self.angle = sum(
            self.angle_history
        ) / len(self.angle_history)

        # Bicep curl rep detection
        if self.angle >= 150:

            self.stage = "DOWN"
            self.feedback = "Now curl the dumbbell upward"

        elif self.angle <= 60:

            if self.stage == "DOWN":
                self.reps += 1

            self.stage = "UP"
            self.feedback = "Good curl! Lower slowly"

        else:
            self.feedback = "Control the movement"

        # Detect excessive upper arm movement
        arm_movement = calculate_angle(
            elbow_point,
            shoulder_point,
            (shoulder_point[0], shoulder_point[1] + 100)
        )

        if arm_movement > 35:
            self.feedback = "Keep your elbow close to your body"

        cv2.line(
            frame,
            shoulder_point,
            elbow_point,
            (0, 255, 255),
            3
        )

        cv2.line(
            frame,
            elbow_point,
            wrist_point,
            (0, 255, 255),
            3
        )

        cv2.circle(
            frame,
            elbow_point,
            8,
            (0, 0, 255),
            -1
        )

        return frame
