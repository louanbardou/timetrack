# TimeTrack

A local, private, always-on time tracker for macOS. Every few seconds it takes
a screenshot, reads the on-screen text with on-device OCR, classifies your
activity into categories using a small local LLM (via [Ollama](https://ollama.com)),
then throws the screenshot away. Only the category label, timestamp, app name,
and confidence score are ever stored.

No screenshot is ever saved to disk or sent anywhere. Everything - OCR,
classification, storage - runs on your machine.

## What you get

- A **menu bar icon** ("TT") showing your current activity and confidence
- A **floating widget** (top-right corner, transparent, draggable, resizable
  between a compact and expanded view) showing minutes per category for
  today / this week / this month, with a live clock and a "last capture"
  readout so you can see it's actually running
- A **full dashboard** (`Open Full Dashboard` from the menu bar) with charts
  for a deeper look
- Auto-starts at login, auto-restarts if it crashes, keeps running even if
  you accidentally close the widget

## Requirements

- macOS (uses Apple's on-device Vision framework for OCR, and AppKit for the
  widget - this will not work on Linux/Windows)
- [Homebrew](https://brew.sh)
- ~6GB free disk space for the local models (Qwen2.5 3B + MiniCPM-V)

## Install

```bash
git clone <this-repo-url> timetrack
cd timetrack
./setup.sh
```

The script installs Python 3.11, Ollama, pulls the two local models, creates
a virtualenv, installs dependencies, and registers a LaunchAgent so it starts
automatically at login.

On first run, macOS will prompt for two permissions:

- **Screen Recording** - to take the periodic screenshot (discarded immediately)
- **Accessibility** - to read the name of the active app/window

Grant both, then run:

```bash
launchctl kickstart -k gui/$(id -u)/com.timetrack.local
```

## Customizing categories

Use **Preferences…** from the menu bar - add, rename, recolor, or delete
categories, and edit each one's description (this is the text the local
model reads to decide, so be specific about what does and doesn't count).
Saving restarts the tracker automatically so changes apply immediately.
Categories are stored in `categories.json` (created on first run, gitignored
since it's per-user state, not source).

For apps that are unambiguous (an IDE, a calling app, a messaging app), add
them to `APP_OVERRIDES` in `config.py` - this skips the LLM entirely for
that app, which is both instant and immune to misclassification. Restart
with the `launchctl kickstart` command above after editing this one, since
it's a source file, not something Preferences writes to.

## Menu bar controls

- **Pause / Resume** - stop or resume capturing
- **Interval** - how often to capture (10-60s)
- **Show/Hide Widget** - toggle the floating widget (it comes back on its own
  if it crashes or you close it with the × button and this is still "shown")
- **Open Full Dashboard** - opens a browser-based dashboard with charts
- **Quit** - stops everything, including the widget

## Project layout

| File | Purpose |
|---|---|
| `config.py` | Categories, colors, model names, capture interval, app overrides |
| `capture.py` | Screenshot + local OCR + active app/window detection |
| `classifier.py` | Local classification (Ollama, JSON-schema-constrained output) |
| `db.py` | SQLite storage |
| `aggregate.py` | Turns raw samples into per-day/week/month totals |
| `tracker.py` | Menu bar app - the main process, runs the capture loop |
| `widget.py` | Floating widget - runs as its own process |
| `dashboard.py` | Generates the full HTML dashboard |
| `setup.sh` | Installer |

## Uninstall

```bash
launchctl bootout gui/$(id -u)/com.timetrack.local
rm ~/Library/LaunchAgents/com.timetrack.local.plist
rm -rf /path/to/timetrack
```

Ollama and the models it downloaded are left in place (`brew uninstall ollama`
and `ollama rm qwen2.5:3b minicpm-v` if you want them gone too).
