"""Floating, transparent, always-on-top widget showing time-per-category.
Runs as its own process (launched by tracker.py) so its native window loop
never conflicts with the menu bar app's run loop.
"""
import json
import threading
import time

import webview
import AppKit

import aggregate
import db
import config

MINI_SIZE = (240, 268)
EXPANDED_SIZE = (300, 580)
MARGIN = 12
REFRESH_SECONDS = 5


def screen_size():
    frame = AppKit.NSScreen.mainScreen().frame()
    return int(frame.size.width), int(frame.size.height)


def top_right_position(width):
    screen_w, _ = screen_size()
    return screen_w - width - MARGIN, MARGIN


class Api:
    def __init__(self):
        self.window = None
        self.expanded = False

    def toggle_expand(self):
        self.expanded = not self.expanded
        size = EXPANDED_SIZE if self.expanded else MINI_SIZE
        x, y = top_right_position(size[0])
        self.window.resize(*size)
        self.window.move(x, y)
        return self.expanded

    def quit_widget(self):
        self.window.destroy()


def render_js(data):
    return f"window.__render({json.dumps(data)});"


CAT_LABELS = {c["id"]: c["label"] for c in config.ALL_CATEGORIES}


def build_payload():
    data = aggregate.get_widget_data()
    last = db.last_sample()  # (ts, app, window_title, category_id, confidence) or None
    if last:
        ts, app, title, cat_id, conf = last
        data["last_ts"] = ts
        data["last_label"] = CAT_LABELS.get(cat_id, cat_id)
    else:
        data["last_ts"] = None
        data["last_label"] = None
    return data


def refresh_loop(window):
    while True:
        try:
            window.evaluate_js(render_js(build_payload()))
        except Exception:
            pass
        time.sleep(REFRESH_SECONDS)


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  html, body {
    margin: 0; padding: 0; background: transparent;
    font-family: -apple-system, "SF Pro Text", system-ui, sans-serif;
    -webkit-user-select: none; user-select: none; overflow: hidden;
  }
  .panel {
    background: rgba(28, 28, 30, 0.72);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 10px 12px 14px;
    color: #f2f2f2;
    height: calc(100vh - 24px);
    box-sizing: border-box;
    overflow: hidden;
  }
  .header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 2px; cursor: default;
  }
  .title-row { display: flex; align-items: center; gap: 6px; }
  .title { font-size: 12px; font-weight: 600; letter-spacing: 0.02em; color: #fff; }
  .pulse-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #30d158;
    animation: pulse 1.6s ease-in-out infinite;
    box-shadow: 0 0 4px rgba(48,209,88,0.8);
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.65); }
  }
  .clock {
    font-variant-numeric: tabular-nums; font-size: 10px;
    color: rgba(255,255,255,0.5); margin-bottom: 8px;
  }
  .last-capture {
    font-size: 10px; color: rgba(255,255,255,0.55);
    margin-bottom: 10px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .last-capture b { color: rgba(255,255,255,0.85); font-weight: 500; }
  .btn {
    -webkit-app-region: no-drag;
    width: 20px; height: 20px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    color: #ccc; font-size: 13px; cursor: pointer;
  }
  .btn:hover { background: rgba(255,255,255,0.12); }
  .section-title {
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em;
    color: rgba(255,255,255,0.5); margin: 10px 0 6px;
  }
  .row { display: flex; align-items: center; margin-bottom: 5px; gap: 6px; }
  .cat-label { width: 92px; font-size: 11px; color: #e6e6e6; flex-shrink: 0;
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bar-track { flex: 1; height: 10px; background: rgba(255,255,255,0.08); border-radius: 5px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 5px; min-width: 2px; }
  .cat-value { width: 40px; text-align: right; font-size: 10px; color: rgba(255,255,255,0.65);
               flex-shrink: 0; font-variant-numeric: tabular-nums; }
  .extra { display: none; }
  .expanded .extra { display: block; }
</style>
</head>
<body>
  <div class="panel" id="panel">
    <div class="header" id="drag-handle">
      <div class="title-row">
        <div class="pulse-dot"></div>
        <div class="title">TimeTrack</div>
      </div>
      <div style="display:flex; gap:4px;">
        <div class="btn" onclick="toggleExpand()" id="expand-btn">⌄</div>
        <div class="btn" onclick="pywebview.api.quit_widget()">×</div>
      </div>
    </div>
    <div class="clock" id="clock">--:--:--</div>
    <div class="last-capture" id="last-capture">Waiting for first capture…</div>
    <div class="section-title">Today</div>
    <div id="today-rows"></div>
    <div class="extra">
      <div class="section-title">This week</div>
      <div id="week-rows"></div>
      <div class="section-title">This month</div>
      <div id="month-rows"></div>
    </div>
  </div>

<script>
function fmt(m) {
  const h = Math.floor(m / 60);
  const mm = Math.round(m % 60);
  return h > 0 ? `${h}h${mm.toString().padStart(2,'0')}` : `${mm}m`;
}

function rows(containerId, labels, colors, minutes) {
  const max = Math.max(1, ...minutes);
  const el = document.getElementById(containerId);
  el.innerHTML = labels.map((label, i) => `
    <div class="row">
      <div class="cat-label">${label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(minutes[i]/max*100).toFixed(0)}%; background:${colors[i]}"></div></div>
      <div class="cat-value">${fmt(minutes[i])}</div>
    </div>
  `).join('');
}

function timeAgo(iso) {
  const diffSec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  return `${Math.round(diffSec / 60)}m ago`;
}

window.__render = function(data) {
  rows('today-rows', data.labels, data.colors_dark, data.today_minutes);
  rows('week-rows', data.labels, data.colors_dark, data.week_minutes);
  rows('month-rows', data.labels, data.colors_dark, data.month_minutes);
  const lc = document.getElementById('last-capture');
  if (data.last_ts) {
    const t = new Date(data.last_ts).toLocaleTimeString();
    lc.innerHTML = `Last capture <b>${t}</b> (${timeAgo(data.last_ts)}) · <b>${data.last_label}</b>`;
  }
};

function tickClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
setInterval(tickClock, 1000);
tickClock();

function toggleExpand() {
  pywebview.api.toggle_expand().then(expanded => {
    document.getElementById('panel').classList.toggle('expanded', expanded);
    document.getElementById('expand-btn').textContent = expanded ? '⌃' : '⌄';
  });
}
</script>
</body>
</html>
"""


def main():
    api = Api()
    x, y = top_right_position(MINI_SIZE[0])
    window = webview.create_window(
        "TimeTrack",
        html=HTML,
        width=MINI_SIZE[0],
        height=MINI_SIZE[1],
        x=x,
        y=y,
        frameless=True,
        easy_drag=True,
        on_top=True,
        transparent=True,
        resizable=False,
        js_api=api,
    )
    api.window = window
    threading.Thread(target=refresh_loop, args=(window,), daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
