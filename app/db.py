import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "courses.db"
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "courses_seed.json"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            days TEXT NOT NULL,
            time TEXT NOT NULL,
            seats_total INTEGER NOT NULL,
            seats_taken INTEGER NOT NULL,
            instructor TEXT NOT NULL
        )
        """
    )
    cur.execute("SELECT COUNT(*) as count FROM courses")
    if cur.fetchone()["count"] == 0:
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        cur.executemany(
            """
            INSERT INTO courses (id, title, subject, days, time, seats_total, seats_taken, instructor)
            VALUES (:id, :title, :subject, :days, :time, :seats_total, :seats_taken, :instructor)
            """,
            courses,
        )
    conn.commit()
    conn.close()


def serialize(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["open_seats"] = d["seats_total"] - d["seats_taken"]
    return d
