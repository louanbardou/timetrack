"""Preferences window: add/edit/delete categories used by the classifier.
Runs as its own short-lived process (launched from the tracker.py menu),
saves to categories.json, then restarts the tracker so changes apply
immediately - restart works by simply killing the running tracker.py, since
the LaunchAgent's KeepAlive relaunches it automatically within a few seconds
regardless of which machine/label this is running under.
"""
import json
import os
import signal
import subprocess

import webview

import config

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def restart_tracker():
    try:
        out = subprocess.run(["pgrep", "-f", os.path.join(PROJECT_DIR, "tracker.py")],
                              capture_output=True, text=True)
        for pid in out.stdout.split():
            if int(pid) != os.getpid():
                os.kill(int(pid), signal.SIGTERM)
    except Exception:
        pass


class Api:
    def save(self, categories):
        cleaned = []
        seen_ids = set()
        for c in categories:
            label = (c.get("label") or "").strip()
            if not label:
                continue
            cid = c.get("id") or ""
            if not cid:
                cid = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_") or "category"
            base_id, i = cid, 2
            while cid in seen_ids:
                cid = f"{base_id}_{i}"
                i += 1
            seen_ids.add(cid)
            color = c.get("color") or "#898781"
            cleaned.append({
                "id": cid,
                "label": label,
                "description": (c.get("description") or "").strip(),
                "color_light": c.get("color_light") or color,
                "color_dark": c.get("color_dark") or color,
            })

        if not any(c["id"] == "autre" for c in cleaned):
            cleaned.append(dict(config.OTHER_CATEGORY))

        config.save_categories(cleaned)
        restart_tracker()
        return True

    def close(self):
        webview.windows[0].destroy()


def render_js():
    cats = [c for c in config.ALL_CATEGORIES if c["id"] != "autre"]
    return f"window.__init({json.dumps(cats)});"


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  :root { color-scheme: dark; }
  html, body {
    margin: 0; padding: 0; height: 100%;
    background: #1e1e1e; color: #eee;
    font-family: -apple-system, "SF Pro Text", system-ui, sans-serif;
  }
  .wrap { padding: 20px; box-sizing: border-box; height: 100%; display: flex; flex-direction: column; }
  h1 { font-size: 15px; margin: 0 0 4px; }
  .sub { font-size: 12px; color: #999; margin-bottom: 16px; }
  .rows { flex: 1; overflow-y: auto; }
  .row {
    background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 10px;
    padding: 10px 12px; margin-bottom: 10px;
  }
  .row-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .row input[type=color] {
    width: 24px; height: 24px; border: none; border-radius: 6px; padding: 0;
    background: none; flex-shrink: 0;
  }
  .row input[type=text] {
    flex: 1; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 6px;
    color: #eee; padding: 6px 8px; font-size: 13px;
  }
  .row textarea {
    width: 100%; box-sizing: border-box; background: #1a1a1a; border: 1px solid #3a3a3a;
    border-radius: 6px; color: #ccc; padding: 6px 8px; font-size: 12px; resize: vertical;
    min-height: 40px; font-family: inherit;
  }
  .del {
    width: 22px; height: 22px; border-radius: 6px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    color: #999; cursor: pointer; font-size: 14px;
  }
  .del:hover { background: #3a3a3a; color: #fff; }
  .add-btn, .save-btn, .cancel-btn {
    border-radius: 8px; padding: 8px 14px; font-size: 13px; cursor: pointer;
    border: 1px solid #3a3a3a; background: #2a2a2a; color: #eee;
  }
  .add-btn { width: 100%; margin-bottom: 4px; }
  .add-btn:hover, .save-btn:hover, .cancel-btn:hover { background: #3a3a3a; }
  .save-btn { background: #2a78d6; border-color: #2a78d6; }
  .save-btn:hover { background: #3987e5; }
  .footer { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
  .hint { font-size: 11px; color: #777; margin-top: 4px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Categories</h1>
  <div class="sub">The description is what the local model reads to decide - be specific about what does and doesn't count.</div>
  <div class="rows" id="rows"></div>
  <div class="add-btn" onclick="addRow()">+ Add category</div>
  <div class="hint">"Autre" (catch-all) is always kept and isn't shown here.</div>
  <div class="footer">
    <div class="cancel-btn" onclick="pywebview.api.close()">Cancel</div>
    <div class="save-btn" onclick="save()">Save &amp; Restart</div>
  </div>
</div>

<script>
let rows = [];

function addRow(cat) {
  rows.push(cat || {id: '', label: '', description: '', color: '#2a78d6'});
  render();
}

function removeRow(i) {
  rows.splice(i, 1);
  render();
}

function render() {
  const el = document.getElementById('rows');
  el.innerHTML = rows.map((r, i) => `
    <div class="row">
      <div class="row-top">
        <input type="color" value="${r.color || r.color_light || '#2a78d6'}" oninput="rows[${i}].color = this.value">
        <input type="text" placeholder="Label" value="${r.label.replace(/"/g, '&quot;')}" oninput="rows[${i}].label = this.value">
        <div class="del" onclick="removeRow(${i})">×</div>
      </div>
      <textarea placeholder="Description (used to prompt the classifier)" oninput="rows[${i}].description = this.value">${r.description}</textarea>
    </div>
  `).join('');
}

function save() {
  pywebview.api.save(rows).then(() => pywebview.api.close());
}

window.__init = function(cats) {
  rows = cats.map(c => ({id: c.id, label: c.label, description: c.description, color: c.color_light, color_light: c.color_light, color_dark: c.color_dark}));
  render();
};
</script>
</body>
</html>
"""


def main():
    api = Api()
    window = webview.create_window(
        "TimeTrack Preferences",
        html=HTML,
        width=460,
        height=620,
        resizable=True,
        js_api=api,
    )
    window.events.loaded += lambda: window.evaluate_js(render_js())
    webview.start()


if __name__ == "__main__":
    main()
