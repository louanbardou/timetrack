"""Daily backup of activity.db with rotation and an integrity check.

Uses sqlite3's own .backup() API (not a raw file copy) so it's safe to run
even while tracker.py might be mid-write - SQLite's backup API takes a
consistent snapshot rather than copying bytes that could be half-written.
"""
import os
import sqlite3
import glob
import time
from datetime import datetime

import config

BACKUP_DIR = os.path.expanduser("~/timetrack/backups")
KEEP_DAILY = 30  # rotate: keep the last 30 daily backups (~1 month of recovery points)
LOG_PATH = os.path.expanduser("~/timetrack/backup.log")


def log(msg):
    with open(LOG_PATH, "a") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")


def check_integrity(path):
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        return result == "ok", result
    finally:
        conn.close()


def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if not os.path.exists(config.DB_PATH):
        log("skip: no activity.db yet")
        return

    ok, detail = check_integrity(config.DB_PATH)
    if not ok:
        log(f"WARNING: integrity check FAILED on live db before backup: {detail}")
        # still attempt the backup - a bad backup of a bad db is better than none,
        # and older rotated backups may still be clean.
    else:
        log("integrity check OK")

    stamp = datetime.now().strftime("%Y-%m-%d")
    dest_path = os.path.join(BACKUP_DIR, f"activity-{stamp}.db")

    src = sqlite3.connect(config.DB_PATH)
    dst = sqlite3.connect(dest_path)
    try:
        src.backup(dst)
        log(f"backed up to {dest_path}")
    finally:
        src.close()
        dst.close()

    _rotate()


def _rotate():
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "activity-*.db")))
    excess = len(backups) - KEEP_DAILY
    for path in backups[:max(0, excess)]:
        os.remove(path)
        log(f"rotated out {path}")


if __name__ == "__main__":
    run_backup()
