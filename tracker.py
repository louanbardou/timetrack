"""Menu bar app: captures + classifies activity on an interval, stores samples,
manages the floating widget subprocess, and opens the full HTML dashboard.
Run with: ./venv/bin/python tracker.py
"""
import os
import sys
import threading
import subprocess
from datetime import datetime, timezone

import rumps

import db
import config
from capture import get_frontmost_app_and_window, capture_screenshot_path, ocr_screenshot, delete_screenshot
from classifier import classify
from dashboard import generate_dashboard

INTERVAL_CHOICES = [10, 15, 20, 30, 60]
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WIDGET_SCRIPT = os.path.join(PROJECT_DIR, "widget.py")


class TimeTrackApp(rumps.App):
    def __init__(self):
        super().__init__("TimeTrack", title="TT")
        self.running = True
        self.interval = config.DEFAULT_INTERVAL_SECONDS
        self.busy = False  # guards against overlapping ticks if classification is slow

        self.status_item = rumps.MenuItem("Starting…")
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        interval_menu = rumps.MenuItem("Interval")
        for secs in INTERVAL_CHOICES:
            item = rumps.MenuItem(f"{secs}s", callback=self.make_interval_setter(secs))
            interval_menu.add(item)

        self.widget_item = rumps.MenuItem("Hide Widget", callback=self.toggle_widget)
        self.widget_proc = None
        self.widget_wanted = True  # watchdog relaunches the widget whenever this is True and it's not running
        self.quit_button = None  # replaced below so we can clean up the widget process first

        self.menu = [
            self.status_item,
            self.pause_item,
            interval_menu,
            None,
            self.widget_item,
            rumps.MenuItem("Open Full Dashboard", callback=self.open_dashboard),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        db.init_db()
        self.start_widget()
        self.timer = rumps.Timer(self.tick, self.interval)
        self.timer.start()

    def start_widget(self):
        self.widget_wanted = True
        if self.widget_proc is None or self.widget_proc.poll() is not None:
            self.widget_proc = subprocess.Popen([sys.executable, WIDGET_SCRIPT])
            self.widget_item.title = "Hide Widget"

    def stop_widget(self):
        self.widget_wanted = False
        if self.widget_proc and self.widget_proc.poll() is None:
            self.widget_proc.terminate()
            self.widget_proc = None
        self.widget_item.title = "Show Widget"

    def toggle_widget(self, sender):
        if self.widget_wanted:
            self.stop_widget()
        else:
            self.start_widget()

    def watchdog_widget(self):
        """Runs on every tick: if the widget is wanted but not alive (crashed,
        or the user closed it with the x button), relaunch it - so 'always
        open' survives more than just a computer restart."""
        if self.widget_wanted and (self.widget_proc is None or self.widget_proc.poll() is not None):
            self.widget_proc = subprocess.Popen([sys.executable, WIDGET_SCRIPT])

    def make_interval_setter(self, secs):
        def _set(sender):
            self.interval = secs
            self.timer.stop()
            self.timer = rumps.Timer(self.tick, self.interval)
            if self.running:
                self.timer.start()
        return _set

    def toggle_pause(self, sender):
        self.running = not self.running
        if self.running:
            sender.title = "Pause"
            self.timer.start()
            self.title = "TT"
        else:
            sender.title = "Resume"
            self.timer.stop()
            self.title = "TT ||"

    def open_dashboard(self, sender):
        path = generate_dashboard()
        subprocess.run(["open", path])

    def quit_app(self, sender):
        self.stop_widget()
        rumps.quit_application()

    def tick(self, sender):
        self.watchdog_widget()
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._do_capture_cycle, daemon=True).start()

    def _do_capture_cycle(self):
        try:
            app, title = get_frontmost_app_and_window()
            screenshot_path = capture_screenshot_path()
            ocr_text = ocr_screenshot(screenshot_path)
            cat_id, conf, used_vision = classify(app, title, ocr_text, screenshot_path)
            delete_screenshot(screenshot_path)

            ts_iso = datetime.now(timezone.utc).astimezone().isoformat()
            db.insert_sample(ts_iso, self.interval, app, title, cat_id, conf, used_vision)

            label = next((c["label"] for c in config.ALL_CATEGORIES if c["id"] == cat_id), cat_id)
            self.status_item.title = f"{label} ({conf:.0%}){' (vision)' if used_vision else ''}"
            self.title = f"TT {label[:12]}"
        except Exception as e:
            self.status_item.title = f"Error: {e}"
        finally:
            self.busy = False


if __name__ == "__main__":
    TimeTrackApp().run()
