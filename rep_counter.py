import cv2
import mediapipe as mp
import numpy as np

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

counter = 0
stage = None

with mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
) as hands:

    while cap.isOpened():
        success, frame = cap.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                # Detect finger positions
                landmarks = hand_landmarks.landmark

                fingers_up = 0

                tips = [8, 12, 16, 20]
                pips = [6, 10, 14, 18]

                for tip, pip in zip(tips, pips):
                    if landmarks[tip].y < landmarks[pip].y:
                        fingers_up += 1

                # Count open-close hand repetitions
                if fingers_up >= 4:
                    stage = "open"

                elif fingers_up <= 1 and stage == "open":
                    stage = "closed"
                    counter += 1

        cv2.putText(
            frame,
            f"Reps: {counter}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3
        )

        cv2.putText(
            frame,
            f"Stage: {stage}",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2
        )

        cv2.imshow("RepSense - Rep Counter", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()