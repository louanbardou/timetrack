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

# Added after the original schema shipped - kept as a migration so existing
# databases (with real history) don't need to be recreated.
MIGRATIONS = [
    ("ocr_snippet", "ALTER TABLE activity ADD COLUMN ocr_snippet TEXT"),
]


def _migrate(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(activity)")}
    for col_name, ddl in MIGRATIONS:
        if col_name not in existing:
            conn.execute(ddl)


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
        _migrate(conn)
        conn.commit()


def insert_sample(ts_iso, interval_seconds, app, window_title, category_id, confidence, used_vision=False, ocr_snippet=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity (ts, interval_seconds, app, window_title, category_id, confidence, used_vision, ocr_snippet) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts_iso, interval_seconds, app, window_title, category_id, confidence, int(used_vision), ocr_snippet),
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
