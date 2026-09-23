"""Capture the active app/window and OCR text from a screenshot.

Privacy: the screenshot file is written to a temp path, OCR'd immediately,
then deleted. No image is ever kept on disk beyond that single OCR call.
"""
import subprocess
import tempfile
import os

from ocrmac import ocrmac
from config import OCR_TEXT_MAX_CHARS


def get_frontmost_app_and_window():
    """Return (app_name, window_title) for the frontmost app via AppleScript.
    Requires Accessibility permission for the process running this (Terminal /
    Python) under System Settings > Privacy & Security > Accessibility.
    """
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        try
            set winTitle to name of front window of (first application process whose frontmost is true)
        on error
            set winTitle to ""
        end try
    end tell
    return frontApp & "||" & winTitle
    '''
    try:
        out = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        parts = out.stdout.strip().split("||")
        app = parts[0] if len(parts) > 0 else "Unknown"
        title = parts[1] if len(parts) > 1 else ""
        return app, title
    except Exception:
        return "Unknown", ""


def capture_screenshot_path():
    """Take a screenshot and return its temp path. Caller owns the file and
    MUST delete it (see delete_screenshot) once done - it is never kept
    beyond a single classification cycle."""
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    subprocess.run(["screencapture", "-x", "-t", "png", path], capture_output=True, timeout=10)
    return path


def ocr_screenshot(path):
    """Run local on-device OCR (Apple Vision framework via ocrmac) on the
    screenshot at `path`. Does not touch the file otherwise."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return ""
        annotations = ocrmac.OCR(path).recognize()
        text = " ".join(a[0] for a in annotations)
        return text[:OCR_TEXT_MAX_CHARS]
    except Exception:
        return ""


def delete_screenshot(path):
    if path and os.path.exists(path):
        os.remove(path)
