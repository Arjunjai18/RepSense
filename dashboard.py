
import cv2
import mediapipe as mp
import math
import time
import threading
import streamlit as st

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av

# -----------------------------
# RepSense - AI Squat Coach
# -----------------------------

DOWN_THRESHOLD = 95
UP_THRESHOLD = 160
MIN_VISIBILITY = 0.5
MET_VALUE = 5.0  # Approximate moderate-intensity exercise

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def calculate_angle(a, b, c):
    angle = math.degrees(
        math.atan2(c[1] - b[1], c[0] - b[0]) -
        math.atan2(a[1] - b[1], a[0] - b[0])
    )
    angle = abs(angle)
    if angle > 180:
        angle = 360 - angle
    return angle


class SquatProcessor(VideoProcessorBase):

    def __init__(self, weight=65):
        self.weight = weight
        self.reps = 0
        self.stage = "STAND"
        self.angle = 0
        self.feedback = "Stand sideways to camera"
        self.start_time = time.monotonic()
        self.lock = threading.Lock()

        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def get_stats(self):
        with self.lock:
            elapsed = time.monotonic() - self.start_time

            # Approximate calories using MET formula.
            calories = (
                MET_VALUE * 3.5 * self.weight / 200
            ) * (elapsed / 60)

            return {
                "reps": self.reps,
                "stage": self.stage,
                "angle": self.angle,
                "feedback": self.feedback,
                "time": elapsed,
                "calories": calories
            }

    def recv(self, frame):

        image = frame.to_ndarray(format="bgr24")
        image = cv2.flip(image, 1)

        height, width, _ = image.shape

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        feedback = "No body detected"
        color = (0, 0, 255)
        angle = 0

        if results.pose_landmarks:

            landmarks = results.pose_landmarks.landmark

            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
            ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

            visibility = min(
                hip.visibility,
                knee.visibility,
                ankle.visibility
            )

            if visibility >= MIN_VISIBILITY:

                hip_point = (
                    int(hip.x * width),
                    int(hip.y * height)
                )

                knee_point = (
                    int(knee.x * width),
                    int(knee.y * height)
                )

                ankle_point = (
                    int(ankle.x * width),
                    int(ankle.y * height)
                )

                angle = calculate_angle(
                    hip_point, knee_point, ankle_point
                )

                with self.lock:

                    if angle <= DOWN_THRESHOLD:
                        self.stage = "DOWN"
                        feedback = "Good! Now stand up"
                        color = (0, 220, 255)

                    elif angle >= UP_THRESHOLD:

                        if self.stage == "DOWN":
                            self.reps += 1

                        self.stage = "STAND"
                        feedback = "Great! Keep going"
                        color = (80, 230, 100)

                    else:
                        feedback = "Keep moving"
                        color = (255, 220, 80)

                    self.angle = angle
                    self.feedback = feedback

                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS
                )

                cv2.line(
                    image, hip_point, knee_point,
                    (0, 255, 255), 3
                )

                cv2.line(
                    image, knee_point, ankle_point,
                    (0, 255, 255), 3
                )

                cv2.circle(
                    image, knee_point, 8, (0, 0, 255), -1
                )

                cv2.putText(
                    image,
                    f"Knee Angle: {int(angle)}",
                    (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )

            else:
                feedback = "Move back - show full body"

        with self.lock:
            self.feedback = feedback

        stats = self.get_stats()

        cv2.rectangle(
            image, (10, 10), (width - 10, 125),
            (25, 25, 25), -1
        )

        cv2.putText(
            image, "REPSENSE - AI SQUAT COACH",
            (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (255, 255, 255), 2
        )

        cv2.putText(
            image, f"REPS: {stats['reps']}",
            (20, 85), cv2.FONT_HERSHEY_SIMPLEX,
            0.9, (80, 230, 100), 2
        )

        cv2.putText(
            image, f"STAGE: {stats['stage']}",
            (220, 85), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (255, 255, 255), 2
        )

        cv2.putText(
            image, feedback,
            (20, height - 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65, color, 2
        )

        return av.VideoFrame.from_ndarray(
            image, format="bgr24"
        )

    def close(self):
        self.pose.close()


# -----------------------------
# Streamlit Dashboard
# -----------------------------

st.set_page_config(
    page_title="RepSense AI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #10141c;
}
.metric-card {
    background: #202936;
    padding: 20px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("💪 RepSense")
st.caption("AI POWERED FITNESS TRACKING SYSTEM")

st.sidebar.title("Workout Settings")

weight = st.sidebar.number_input(
    "Body Weight (kg)",
    min_value=30,
    max_value=200,
    value=65,
    step=1
)

st.sidebar.info(
    "Exercise: Squats\n\n"
    "Detection: MediaPipe Pose\n\n"
    "Processing: Local webcam"
)

st.subheader("Live Workout Dashboard")
ctx = webrtc_streamer(
    key="repsense-camera",
    video_processor_factory=lambda: SquatProcessor(weight),
    media_stream_constraints={
        "video": True,
        "audio": False
    },
    rtc_configuration={
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]}
        ]
    },
    async_processing=True
)

st.markdown("---")

st.subheader("Workout Statistics")

col1, col2, col3, col4 = st.columns(4)

rep_display = col1.empty()
calorie_display = col2.empty()
timer_display = col3.empty()
angle_display = col4.empty()

if ctx.state.playing:

    processor = ctx.video_processor

    if processor:
        stats = processor.get_stats()

        minutes = int(stats["time"] // 60)
        seconds = int(stats["time"] % 60)

        rep_display.metric(
            "Squat Repetitions",
            stats["reps"]
        )

        calorie_display.metric(
            "Calories Burned",
            f"{stats['calories']:.1f} kcal"
        )

        timer_display.metric(
            "Workout Duration",
            f"{minutes:02d}:{seconds:02d}"
        )

        angle_display.metric(
            "Knee Angle",
            f"{int(stats['angle'])}°"
        )

    else:
        st.info("Connecting to camera...")

else:
    rep_display.metric("Squat Repetitions", 0)
    calorie_display.metric("Calories Burned", "0.0 kcal")
    timer_display.metric("Workout Duration", "00:00")
    angle_display.metric("Knee Angle", "--")

st.markdown("---")

st.caption(
    "RepSense | AI Fitness Coach | "
    "Calories are approximate estimates, not measured values."
)
