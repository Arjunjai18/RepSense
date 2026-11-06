
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "repsense.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
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


def save_workout(stats, exercise):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO workouts (
                exercise,
                reps,
                calories,
                duration,
                average_angle,
                form_score,
                feedback,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exercise,
            stats.get("reps", 0),
            stats.get("calories", 0),
            stats.get("time", 0),
            stats.get("angle", 0),
            stats.get("form_score", 0),
            stats.get("feedback", ""),
            datetime.now().isoformat(timespec="seconds")
        ))


def get_workouts(limit=100):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM workouts
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]


def get_analytics():
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
