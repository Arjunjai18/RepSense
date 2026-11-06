import os
import cv2
import mediapipe as mp
import math
import time
import threading
import base64
import numpy as np

from flask import Flask, render_template, request, jsonify
from pathlib import Path

from database import (
    initialize_database,
    save_workout,
    get_workouts,
    get_analytics
)

from exercises.squat import SquatDetector
from exercises.pushup import PushupDetector
from exercises.bicep_curl import BicepCurlDetector


# ----------------------------------
# RepSense - Flask Backend
# ----------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "frontend" / "templates"),
    static_folder=str(BASE_DIR / "frontend" / "static"),
    static_url_path="/static"
)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

MIN_VISIBILITY = 0.5

EXERCISES = {
    "squat": SquatDetector,
    "pushup": PushupDetector,
    "bicep_curl": BicepCurlDetector
}

EXERCISE_NAMES = {
    "squat": "Squats",
    "pushup": "Push-ups",
    "bicep_curl": "Bicep Curls"
}

MET_VALUES = {
    "squat": 5.0,
    "pushup": 8.0,
    "bicep_curl": 3.5
}


# ----------------------------------
# Workout Session
# ----------------------------------

class WorkoutSession:

    def __init__(self, weight=65, exercise="squat"):

        self.weight = weight
        self.exercise = exercise

        self.detector = EXERCISES[exercise]()

        self.start_time = time.monotonic()
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.feedback = "Position yourself in front of the camera"

    def get_form_score(self):

        feedback = self.feedback.lower()

        if "not detected" in feedback or "show your" in feedback:
            return 0

        if any(word in feedback for word in [
            "keep your body straight",
            "keep your elbow close",
            "move back",
            "keep your arm visible"
        ]):
            return 60

        if any(word in feedback for word in [
            "good",
            "great"
        ]):
            return 95

        return 80

    def get_stats(self):

        elapsed = time.monotonic() - self.start_time

        met = MET_VALUES[self.exercise]

        calories = (
            met * 3.5 * self.weight / 200
        ) * (elapsed / 60)

        return {
            "exercise": self.exercise,
            "exercise_name": EXERCISE_NAMES[self.exercise],
            "reps": self.detector.reps,
            "stage": self.detector.stage,
            "angle": round(self.detector.angle),
            "angle_label": (
                "Knee Angle"
                if self.exercise == "squat"
                else "Elbow Angle"
            ),
            "feedback": self.feedback,
            "time": round(elapsed, 1),
            "calories": round(calories, 1),
            "form_score": self.get_form_score()
        }

    def process_frame(self, frame):

        frame = cv2.flip(frame, 1)

        height, width, _ = frame.shape

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = self.pose.process(rgb)

        if results.pose_landmarks:

            landmarks = results.pose_landmarks.landmark

            self.detector.process(
                frame,
                landmarks,
                width,
                height
            )

            self.feedback = self.detector.feedback

            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )

        else:

            self.feedback = "Body not detected. Adjust your camera position."

        stats = self.get_stats()

        # Camera overlay
        cv2.rectangle(
            frame,
            (10, 10),
            (width - 10, 115),
            (25, 25, 25),
            -1
        )

        cv2.putText(
            frame,
            "REPSENSE AI COACH",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"EXERCISE: {EXERCISE_NAMES[self.exercise]}",
            (20, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"REPS: {self.detector.reps}",
            (20, 102),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (80, 230, 100),
            2
        )

        cv2.putText(
            frame,
            self.feedback[:65],
            (20, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (80, 230, 100),
            2
        )

        return frame, stats

    def close(self):
        self.pose.close()


# ----------------------------------
# Session Management
# ----------------------------------

current_session = None
session_lock = threading.Lock()


def finish_current_session():

    global current_session

    if current_session is not None:

        stats = current_session.get_stats()
        exercise = current_session.exercise

        save_workout(stats, exercise)

        current_session.close()
        current_session = None

        return stats

    return None


# ----------------------------------
# Initialize Database
# ----------------------------------

initialize_database()


# ----------------------------------
# Website Routes
# ----------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/history")
def history_page():
    return render_template("history.html")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")


# ----------------------------------
# Start Workout
# ----------------------------------

@app.route("/api/start", methods=["POST"])
def start_workout():

    global current_session

    data = request.get_json(silent=True) or {}

    try:

        weight = float(data.get("weight", 65))

        if not math.isfinite(weight) or not 30 <= weight <= 200:
            raise ValueError()

    except (TypeError, ValueError):

        return jsonify({
            "error": "Weight must be between 30 and 200 kg"
        }), 400

    exercise = data.get("exercise", "squat")

    if exercise not in EXERCISES:

        return jsonify({
            "error": "Invalid exercise selected"
        }), 400

    with session_lock:

        if current_session is not None:
            finish_current_session()

        current_session = WorkoutSession(
            weight=weight,
            exercise=exercise
        )

    return jsonify({
        "message": "Workout started",
        "status": "running",
        "exercise": exercise
    })


# ----------------------------------
# Process Camera Frames
# ----------------------------------

@app.route("/api/frame", methods=["POST"])
def process_video_frame():

    with session_lock:

        if current_session is None:

            return jsonify({
                "error": "Start a workout first"
            }), 400

        data = request.get_json(silent=True) or {}

        frame_data = data.get("frame", "")

        if not frame_data:

            return jsonify({
                "error": "No frame received"
            }), 400

        try:

            encoded = frame_data.split(",", 1)[-1]

            image_bytes = base64.b64decode(
                encoded,
                validate=True
            )

            image_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )

            if frame is None:

                return jsonify({
                    "error": "Invalid image frame"
                }), 400

            processed_frame, stats = current_session.process_frame(frame)

            success, buffer = cv2.imencode(
                ".jpg",
                processed_frame,
                [cv2.IMWRITE_JPEG_QUALITY, 75]
            )

            if not success:

                return jsonify({
                    "error": "Could not encode frame"
                }), 500

            image_base64 = base64.b64encode(
                buffer.tobytes()
            ).decode("utf-8")

            return jsonify({
                "image": "data:image/jpeg;base64," + image_base64,
                "stats": stats
            })

        except Exception:

            app.logger.exception("Frame processing failed")

            return jsonify({
                "error": "Frame processing failed"
            }), 500


# ----------------------------------
# Stop Workout and Save to Database
# ----------------------------------

@app.route("/api/stop", methods=["POST"])
def stop_workout():

    with session_lock:

        if current_session is not None:

            stats = finish_current_session()

            return jsonify({
                "message": "Workout stopped and saved",
                "stats": stats
            })

    return jsonify({
        "message": "No active workout"
    })


# ----------------------------------
# Workout History API
# ----------------------------------

@app.route("/api/history")
def workout_history():

    return jsonify({
        "workouts": get_workouts()
    })


# ----------------------------------
# Analytics API
# ----------------------------------

@app.route("/api/analytics")
def workout_analytics():

    return jsonify(get_analytics())


# ----------------------------------
# Run Server
# ----------------------------------

if __name__ == "__main__":

    print("RepSense AI server starting...")
    print("Open http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        threaded=True
    )
