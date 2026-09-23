"""SQLite storage for classified activity samples."""
import sqlite3
from contextlib import contextmanager
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,              -- ISO timestamp of the sample
    interval_seconds INTEGER NOT NULL,  -- how long this sample represents
    app TEXT,
    window_title TEXT,
    category_id TEXT NOT NULL,
    confidence REAL,
    used_vision INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_activity_ts ON activity(ts);
CREATE INDEX IF NOT EXISTS idx_activity_category ON activity(category_id);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    # WAL is more resilient than the default rollback journal (better
    # crash/power-loss behavior, and lets the widget read without blocking
    # on the tracker's writes).
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def insert_sample(ts_iso, interval_seconds, app, window_title, category_id, confidence, used_vision=False):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity (ts, interval_seconds, app, window_title, category_id, confidence, used_vision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts_iso, interval_seconds, app, window_title, category_id, confidence, int(used_vision)),
        )
        conn.commit()


def fetch_range(start_iso, end_iso):
    """Return all samples with ts in [start_iso, end_iso)."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT ts, interval_seconds, app, window_title, category_id, confidence "
            "FROM activity WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start_iso, end_iso),
        )
        return cur.fetchall()


def last_sample():
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT ts, app, window_title, category_id, confidence FROM activity ORDER BY id DESC LIMIT 1"
        )
        return cur.fetchone()
