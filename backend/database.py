
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "repsense.db"


def use_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if bool(url) != bool(key):
        raise RuntimeError(
            "Both SUPABASE_URL and SUPABASE_KEY must be configured."
        )

    return bool(url and key)


def supabase_request(method, endpoint, payload=None):
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]

    request = Request(
        f"{url}/rest/v1/{endpoint}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers={
    "apikey": key,
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}
    )

    try:
        with urlopen(request, timeout=20) as response:
            result = response.read().decode("utf-8")
            return json.loads(result) if result else None

    except HTTPError as error:
        details = error.read().decode("utf-8")
        raise RuntimeError(f"Supabase error: {details}") from error

    except URLError as error:
        raise RuntimeError(f"Could not connect to Supabase: {error}") from error


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    if use_supabase():
        supabase_request(
            "GET",
            "workouts?select=id&limit=1"
        )
        print("Supabase database connected successfully.")
        return

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise TEXT NOT NULL,
                reps INTEGER NOT NULL DEFAULT 0,
                calories REAL NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                average_angle REAL NOT NULL DEFAULT 0,
                form_score INTEGER NOT NULL DEFAULT 0,
                feedback TEXT,
                completed_at TEXT NOT NULL
            )
        """)

    print("Local SQLite database initialized.")


def save_workout(stats, exercise):
    workout = {
        "exercise": exercise,
        "reps": stats.get("reps", 0),
        "calories": stats.get("calories", 0),
        "duration": stats.get("time", 0),
        "average_angle": stats.get("angle", 0),
        "form_score": stats.get("form_score", 0),
        "feedback": stats.get("feedback", ""),
        "completed_at": datetime.now().astimezone().isoformat()
    }

    if use_supabase():
        supabase_request("POST", "workouts", workout)
        return

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO workouts (
                exercise, reps, calories, duration,
                average_angle, form_score, feedback, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workout["exercise"],
            workout["reps"],
            workout["calories"],
            workout["duration"],
            workout["average_angle"],
            workout["form_score"],
            workout["feedback"],
            workout["completed_at"]
        ))


def get_workouts(limit=100):
    if use_supabase():
        query = urlencode({
            "select": "*",
            "order": "id.desc",
            "limit": limit
        })
        return supabase_request("GET", f"workouts?{query}") or []

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM workouts
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]


def get_analytics():
    if use_supabase():
        rows = get_workouts(limit=1000)

        summary = {
            "sessions": len(rows),
            "total_reps": sum(row["reps"] or 0 for row in rows),
            "total_calories": sum(row["calories"] or 0 for row in rows),
            "total_duration": sum(row["duration"] or 0 for row in rows),
            "average_form": (
                sum(row["form_score"] or 0 for row in rows) / len(rows)
                if rows else 0
            )
        }

        daily_data = {}
        exercise_data = {}

        for row in rows:
            day = row["completed_at"][:10]

            if day not in daily_data:
                daily_data[day] = {
                    "day": day,
                    "reps": 0,
                    "sessions": 0
                }

            daily_data[day]["reps"] += row["reps"] or 0
            daily_data[day]["sessions"] += 1

            exercise = row["exercise"]
            exercise_data[exercise] = (
                exercise_data.get(exercise, 0) + (row["reps"] or 0)
            )

        daily = sorted(
            daily_data.values(),
            key=lambda item: item["day"]
        )[-7:]

        exercises = [
            {"exercise": name, "reps": reps}
            for name, reps in exercise_data.items()
        ]

        return {
            "summary": summary,
            "daily": daily,
            "exercises": exercises
        }

    with get_connection() as connection:
        total = connection.execute("""
            SELECT
                COUNT(*) AS sessions,
                COALESCE(SUM(reps), 0) AS total_reps,
                COALESCE(SUM(calories), 0) AS total_calories,
                COALESCE(SUM(duration), 0) AS total_duration,
                COALESCE(AVG(form_score), 0) AS average_form
            FROM workouts
        """).fetchone()

        daily = connection.execute("""
            SELECT
                DATE(completed_at) AS day,
                SUM(reps) AS reps,
                COUNT(*) AS sessions
            FROM workouts
            GROUP BY DATE(completed_at)
            ORDER BY day DESC
            LIMIT 7
        """).fetchall()

        exercises = connection.execute("""
            SELECT exercise, SUM(reps) AS reps
            FROM workouts
            GROUP BY exercise
        """).fetchall()

        return {
            "summary": dict(total),
            "daily": [dict(row) for row in reversed(daily)],
            "exercises": [dict(row) for row in exercises]
        }
