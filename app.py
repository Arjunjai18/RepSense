import cv2
import mediapipe as mp
import math
from collections import deque

# -----------------------------
# RepSense - AI Squat Coach
# Local webcam processing only
# -----------------------------

CAMERA_INDEX = 0
DOWN_THRESHOLD = 95       # Knee angle at or below this = squat bottom
UP_THRESHOLD = 160        # Knee angle at or above this = standing
SMOOTHING_FRAMES = 5      # Average recent angles to reduce jitter
MIN_VISIBILITY = 0.5

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def calculate_angle(a, b, c):
    """Calculate angle ABC (in degrees), where b is the joint."""
    angle = math.degrees(
        math.atan2(c[1] - b[1], c[0] - b[0]) -
        math.atan2(a[1] - b[1], a[0] - b[0])
    )
    angle = abs(angle)
    if angle > 180:
        angle = 360 - angle
    return angle


def landmark_point(landmarks, landmark_id, width, height):
    """Convert a normalized MediaPipe landmark into pixel coordinates."""
    landmark = landmarks[landmark_id]
    return (int(landmark.x * width), int(landmark.y * height))


def draw_text(frame, text, position, scale=0.7, color=(255, 255, 255), thickness=2):
    cv2.putText(
        frame, text, position, cv2.FONT_HERSHEY_SIMPLEX,
        scale, color, thickness, cv2.LINE_AA
    )


def main():
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("ERROR: Could not open your webcam.")
        print("Try changing CAMERA_INDEX to 1 in app.py, or check camera permissions.")
        return

    reps = 0
    stage = "STAND"
    angle_history = deque(maxlen=SMOOTHING_FRAMES)
    displayed_angle = None
    feedback = "Stand sideways to the camera"
    feedback_color = (0, 220, 255)

    print("RepSense is running. Press Q in the camera window to quit.")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:

        while True:
            success, frame = camera.read()
            if not success:
                print("Could not read a frame from the webcam.")
                break

            # Mirror the image so movement feels natural.
            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape

            # MediaPipe expects RGB images.
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = pose.process(rgb_frame)
            rgb_frame.flags.writeable = True

            visible = False

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                # Use the left hip, knee and ankle. Stand sideways so
                # these joints are visible to the camera.
                hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
                knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
                ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

                visibility_ok = min(
                    hip.visibility, knee.visibility, ankle.visibility
                ) >= MIN_VISIBILITY

                if visibility_ok:
                    visible = True
                    hip_point = landmark_point(
                        landmarks, mp_pose.PoseLandmark.LEFT_HIP.value, width, height
                    )
                    knee_point = landmark_point(
                        landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value, width, height
                    )
                    ankle_point = landmark_point(
                        landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value, width, height
                    )

                    raw_angle = calculate_angle(hip_point, knee_point, ankle_point)
                    angle_history.append(raw_angle)
                    displayed_angle = sum(angle_history) / len(angle_history)

                    # State machine: only count after DOWN followed by UP.
                    if displayed_angle <= DOWN_THRESHOLD:
                        stage = "DOWN"
                        feedback = "Good! Now stand up"
                        feedback_color = (0, 220, 255)

                    elif displayed_angle >= UP_THRESHOLD:
                        if stage == "DOWN":
                            reps += 1
                            stage = "STAND"
                        feedback = "Great! Keep going"
                        feedback_color = (80, 230, 100)

                    else:
                        feedback = "Keep moving"
                        feedback_color = (255, 220, 80)

                    # Draw landmarks and skeleton.
                    mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(
                            color=(80, 220, 100), thickness=2, circle_radius=3
                        ),
                        mp_drawing.DrawingSpec(
                            color=(255, 180, 50), thickness=2, circle_radius=2
                        )
                    )

                    # Highlight the three joints used for angle calculation.
                    cv2.line(frame, hip_point, knee_point, (0, 255, 255), 4)
                    cv2.line(frame, knee_point, ankle_point, (0, 255, 255), 4)
                    cv2.circle(frame, knee_point, 8, (0, 0, 255), -1)

                    draw_text(
                        frame, f"{int(displayed_angle)} deg",
                        (knee_point[0] + 12, knee_point[1] - 12),
                        scale=0.7, color=(0, 255, 255)
                    )
                else:
                    feedback = "Move back so your hip, knee and ankle are visible"
                    feedback_color = (0, 165, 255)
            else:
                feedback = "No body detected - stand in front of camera"
                feedback_color = (0, 0, 255)

            # Dashboard overlay.
            cv2.rectangle(frame, (10, 10), (width - 10, 145), (25, 25, 25), -1)
            draw_text(frame, "REPSENSE | AI SQUAT COACH", (25, 42), 0.8)
            draw_text(frame, f"REPS: {reps}", (25, 85), 0.9, (80, 230, 100))
            draw_text(frame, f"STATE: {stage}", (220, 85), 0.7)
            angle_text = f"KNEE ANGLE: {int(displayed_angle)} deg" if displayed_angle is not None else "KNEE ANGLE: --"
            draw_text(frame, angle_text, (25, 120), 0.65)
            draw_text(frame, feedback, (25, height - 25), 0.65, feedback_color)

            if not visible:
                draw_text(frame, "SIDE VIEW | FULL BODY IN FRAME", (25, 175), 0.55, (255, 255, 255))

            cv2.imshow("RepSense - Press Q to quit", frame)

            # Press Q to exit.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    camera.release()
    cv2.destroyAllWindows()
    print(f"Workout finished. Total squats: {reps}")


if __name__ == "__main__":
    main()
