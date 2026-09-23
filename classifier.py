"""Local, free, JEV-style classifier: state in (app + window title + OCR text),
one typed 'choice' out (category id) with a confidence score - via a local
Ollama model constrained to a JSON schema, so the output can't be an invalid
category. Falls back to a vision pass on low confidence.
"""
import json
import base64
import requests

from config import (
    ALL_CATEGORIES, CATEGORY_IDS, TEXT_MODEL, VISION_MODEL, OLLAMA_HOST,
    CONFIDENCE_THRESHOLD, APP_OVERRIDES,
)

CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {
        "category_id": {"type": "string", "enum": CATEGORY_IDS},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["category_id", "confidence"],
}


def _categories_prompt_block():
    lines = []
    for c in ALL_CATEGORIES:
        lines.append(f'- {c["id"]}: {c["label"]} — {c["description"]}')
    return "\n".join(lines)


def classify_text(app, window_title, ocr_text):
    """Text-only 'Choice' classification, JEV-style: typed output, no free text."""
    prompt = f"""You are a fast activity classifier. Given the state below, choose exactly one category id from the list and give a calibrated confidence (0 to 1) that this is the right category. Respond with JSON only, matching the schema.

IMPORTANT: the active app is the strongest signal for what category this is. Only use
the window title or on-screen text to disambiguate when the app itself is generic
(e.g. a web browser). A word like "meeting" or "call" appearing in a window title,
file name, or on-screen text is NOT by itself evidence of the "meeting" category -
that category requires the active app itself to be a live calling app. If the app
and the text seem to disagree, trust the app.

Categories:
{_categories_prompt_block()}

State:
- Active app: {app}
- Window title: {window_title}
- On-screen text (OCR, may be noisy/partial): {ocr_text or "(none)"}
"""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": TEXT_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": CATEGORY_SCHEMA,
                "options": {"temperature": 0.1},
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["response"])
        cat_id = data.get("category_id")
        conf = float(data.get("confidence", 0))
        if cat_id not in CATEGORY_IDS:
            return "autre", 0.0
        return cat_id, conf
    except Exception:
        return "autre", 0.0


def classify_vision(app, window_title, screenshot_path):
    """Vision fallback for low-confidence text classifications: show the model
    the actual screenshot instead of just OCR text."""
    try:
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
        prompt = f"""Look at this screenshot. Active app: {app}. Window title: {window_title}.
Choose exactly one category id from the list below and a confidence (0 to 1). Respond with JSON only.

Categories:
{_categories_prompt_block()}
"""
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
                "format": CATEGORY_SCHEMA,
                "options": {"temperature": 0.1},
            },
            timeout=45,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["response"])
        cat_id = data.get("category_id")
        conf = float(data.get("confidence", 0))
        if cat_id not in CATEGORY_IDS:
            return "autre", 0.0
        return cat_id, conf
    except Exception:
        return "autre", 0.0


def classify(app, window_title, ocr_text, screenshot_path_for_fallback=None):
    """Full pipeline: deterministic app override first (instant, free, always
    right for unambiguous apps), else text classify (fast/free), escalating to
    vision only if confidence is low and a screenshot path was provided."""
    if app in APP_OVERRIDES:
        return APP_OVERRIDES[app], 1.0, False

    cat_id, conf = classify_text(app, window_title, ocr_text)
    used_vision = False
    if conf < CONFIDENCE_THRESHOLD and screenshot_path_for_fallback:
        v_cat, v_conf = classify_vision(app, window_title, screenshot_path_for_fallback)
        if v_conf >= conf:
            cat_id, conf, used_vision = v_cat, v_conf, True
    return cat_id, conf, used_vision
