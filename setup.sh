#!/usr/bin/env bash
# One-shot installer for TimeTrack: local, private activity tracker for macOS.
# Safe to re-run - every step is idempotent.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_LABEL="com.timetrack.local"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "==> TimeTrack setup"
echo "    project dir: $PROJECT_DIR"

# --- 1. Homebrew -----------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo "!! Homebrew is required but not found. Install it from https://brew.sh and re-run this script."
  exit 1
fi

# --- 2. Python 3.11 (needed for rumps/pyobjc/pywebview compatibility) ------
if ! command -v python3.11 >/dev/null 2>&1; then
  echo "==> Installing python@3.11 via Homebrew..."
  brew install python@3.11
fi
PYTHON311="$(brew --prefix python@3.11)/bin/python3.11"

# --- 3. Ollama ---------------------------------------------------------------
if ! command -v ollama >/dev/null 2>&1; then
  echo "==> Installing Ollama via Homebrew..."
  brew install ollama
fi
echo "==> Starting Ollama as a background service (auto-starts at login)..."
brew services start ollama >/dev/null 2>&1 || true
sleep 2

echo "==> Pulling local models (this can take a few minutes the first time)..."
ollama pull qwen2.5:3b
ollama pull minicpm-v

# --- 4. Python virtualenv ----------------------------------------------------
if [ ! -d "$PROJECT_DIR/venv" ]; then
  echo "==> Creating virtualenv..."
  "$PYTHON311" -m venv "$PROJECT_DIR/venv"
fi
echo "==> Installing Python dependencies..."
"$PROJECT_DIR/venv/bin/pip" install -q --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

# --- 5. Initialize the database ---------------------------------------------
(cd "$PROJECT_DIR" && "$PROJECT_DIR/venv/bin/python" -c "import db; db.init_db()")

# --- 6. LaunchAgent: auto-start at login, auto-restart on crash ------------
echo "==> Installing the LaunchAgent (auto-start at login)..."
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_DIR}/venv/bin/python</string>
        <string>${PROJECT_DIR}/tracker.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/tracker.out.log</string>

    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/tracker.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

# --- 7. LaunchAgent: daily database backup ----------------------------------
echo "==> Installing the daily backup LaunchAgent..."
BACKUP_LABEL="${PLIST_LABEL}.backup"
BACKUP_PLIST_PATH="$HOME/Library/LaunchAgents/${BACKUP_LABEL}.plist"
cat > "$BACKUP_PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${BACKUP_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_DIR}/venv/bin/python</string>
        <string>${PROJECT_DIR}/backup.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/backup.out.log</string>

    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/backup.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${BACKUP_LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$BACKUP_PLIST_PATH"

echo ""
echo "==> Done. TimeTrack is running."
echo ""
echo "IMPORTANT - macOS will ask for two permissions the first time it captures:"
echo "  1. Screen Recording  - needed to take the periodic screenshot (deleted"
echo "     immediately after OCR, never saved to disk)."
echo "  2. Accessibility     - needed to read the active app/window name."
echo "  Grant both to 'Python' (or your terminal, if prompted) in:"
echo "  System Settings > Privacy & Security > Screen Recording / Accessibility"
echo ""
echo "  After granting permissions, restart it once with:"
echo "  launchctl kickstart -k gui/\$(id -u)/${PLIST_LABEL}"
echo ""
echo "Look for the 'TT' icon in your menu bar, and a small floating widget"
echo "in the top-right corner of your screen."
echo ""
echo "To edit your categories, use Preferences... from the menu bar icon."
echo ""
echo "Your activity database is backed up daily at 3am (and once now) to"
echo "${PROJECT_DIR}/backups/ - last 30 days are kept."
