"""Configuration: categories, colors, model names, capture interval."""

# Each category: (label, description used in the classifier prompt, palette color)
# Colors from the validated categorical palette (dataviz skill reference), slots 1-6.
CATEGORIES = [
    {
        "id": "emails_slack",
        "label": "Emails/Slack/Messages",
        "description": "Reading or writing email, Slack, Messages, Discord, any chat/messaging app or webmail.",
        "color_light": "#2a78d6",
        "color_dark": "#3987e5",
    },
    {
        "id": "phd",
        "label": "PhD",
        "description": "PhD-related work: reading/writing papers, analysis, thesis work, lab meetings, supervision, anything directly tied to the PhD project.",
        "color_light": "#eb6834",
        "color_dark": "#d95926",
    },
    {
        "id": "divertissement",
        "label": "Divertissement",
        "description": "Entertainment: YouTube, streaming, games, social media browsing (Instagram/TikTok/X/Reddit for leisure), music apps, unrelated news reading.",
        "color_light": "#1baf7a",
        "color_dark": "#199e70",
    },
    {
        "id": "investissement",
        "label": "Investissement/Capitalisation",
        "description": "Personal finance, investing, trading platforms, portfolio tracking, market research, crypto, real estate or business capitalization work.",
        "color_light": "#eda100",
        "color_dark": "#c98500",
    },
    {
        "id": "recherche",
        "label": "Recherche",
        "description": "General research not tied to the PhD specifically: reading articles, papers, documentation, exploring a topic, web search for learning.",
        "color_light": "#e87ba4",
        "color_dark": "#d55181",
    },
    {
        "id": "coding",
        "label": "Coding",
        "description": (
            "The active app itself is a code editor, IDE, or terminal (e.g. Terminal, iTerm, "
            "VS Code, Cursor, Xcode, PyCharm, Jupyter). This applies even if the on-screen text, "
            "file names, or scrollback happen to mention unrelated words like 'meeting' or 'call' - "
            "what matters is that the app being used is a coding tool, not what words appear in it."
        ),
        "color_light": "#008300",
        "color_dark": "#008300",
    },
    {
        "id": "meeting",
        "label": "Meeting",
        "description": (
            "The active app itself is a live video/audio calling app: Zoom, Google Meet, Microsoft "
            "Teams, FaceTime, Skype, or a Discord/Slack voice-video call screen. Do NOT choose this "
            "just because the word 'meeting', 'call', or 'zoom' appears somewhere in a window title, "
            "file name, or on-screen text (e.g. a terminal or document mentioning a past meeting is "
            "NOT this category) - the calling app must actually be the one in the foreground."
        ),
        "color_light": "#4a3aa7",
        "color_dark": "#9085e9",
    },
]

# Deterministic app -> category overrides for unambiguous apps. Checked before
# the LLM call: a small local model can be fooled by incidental keywords in a
# window title or on-screen text (e.g. a Terminal window titled with the word
# "meeting" in it), whereas the app identity itself is a much stronger and
# cheaper signal for these cases. Skips the LLM entirely (instant, free, and
# always confidence 1.0) when the active app matches.
APP_OVERRIDES = {
    "Terminal": "coding",
    "iTerm2": "coding",
    "iTerm": "coding",
    "Code": "coding",
    "Visual Studio Code": "coding",
    "Cursor": "coding",
    "Xcode": "coding",
    "PyCharm": "coding",
    "zoom.us": "meeting",
    "Zoom": "meeting",
    "Microsoft Teams": "meeting",
    "FaceTime": "meeting",
    "Skype": "meeting",
    # Messaging apps: overwhelmingly used for messages/DMs, not calls, and a
    # small model flip-flops on these between "emails_slack" and "meeting"
    # given the exact same, unchanged window content (observed live: same
    # Slack DM title classified 5 different ways in a row with temperature
    # 0.1). Deterministic mapping matches the category's own definition
    # ("Emails/Slack/Messages") and removes that instability entirely.
    "Slack": "emails_slack",
    "Messages": "emails_slack",
    "Mail": "emails_slack",
    "Outlook": "emails_slack",
    "Discord": "emails_slack",
    "WhatsApp": "emails_slack",
}

# Fallback bucket when the classifier can't confidently assign one of the above.
OTHER_CATEGORY = {
    "id": "autre",
    "label": "Autre",
    "description": "Anything that clearly does not fit the other categories (system settings, file management, idle screen, etc).",
    "color_light": "#898781",
    "color_dark": "#898781",
}

ALL_CATEGORIES = CATEGORIES + [OTHER_CATEGORY]
CATEGORY_IDS = [c["id"] for c in ALL_CATEGORIES]

# Confidence below this triggers a vision fallback pass (if enabled) instead of
# trusting the text-only classification.
CONFIDENCE_THRESHOLD = 0.55

# Ollama models
TEXT_MODEL = "qwen2.5:3b"
VISION_MODEL = "minicpm-v"
OLLAMA_HOST = "http://localhost:11434"

# Capture interval in seconds (can be changed live from the menu bar app)
DEFAULT_INTERVAL_SECONDS = 15

# Max characters of OCR text sent to the classifier (keeps prompts fast)
OCR_TEXT_MAX_CHARS = 800

# SQLite DB path
import os
DB_PATH = os.path.expanduser("~/timetrack/activity.db")
