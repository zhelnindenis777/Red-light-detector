from pathlib import Path
from datetime import datetime
import sqlite3


DB_PATH = Path(__file__).resolve().parents[1] / "history.db"


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                media_type TEXT NOT NULL,
                vehicle_count INTEGER NOT NULL,
                violation_count INTEGER NOT NULL,
                red_light INTEGER NOT NULL,
                processing_time REAL NOT NULL,
                result_url TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )


def add_request(**values):
    values["timestamp"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    fields = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    with connect() as connection:
        cursor = connection.execute(
            f"INSERT INTO requests ({fields}) VALUES ({placeholders})",
            tuple(values.values()),
        )
        return cursor.lastrowid


def get_history(limit=50):
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def clear_history():
    with connect() as connection:
        connection.execute("DELETE FROM requests")
