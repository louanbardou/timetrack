"""Shared aggregation logic used by both the full dashboard (dashboard.py)
and the floating widget (widget.py)."""
from datetime import datetime, timedelta

import db
from config import ALL_CATEGORIES

CAT_META = {c["id"]: c for c in ALL_CATEGORIES}
CAT_ORDER = [c["id"] for c in ALL_CATEGORIES]


def _day_str(dt):
    return dt.strftime("%Y-%m-%d")


def _aggregate_by_day(rows):
    """rows: list of (ts, interval_seconds, app, window_title, category_id, confidence)
    Returns: {day_str: {category_id: seconds}}"""
    by_day = {}
    for ts, interval_seconds, app, title, cat_id, conf in rows:
        dt = datetime.fromisoformat(ts)
        day = _day_str(dt)
        by_day.setdefault(day, {})
        by_day[day][cat_id] = by_day[day].get(cat_id, 0) + interval_seconds
    return by_day


def get_data():
    now = datetime.now().astimezone()
    start_month = now - timedelta(days=30)
    rows = db.fetch_range(start_month.isoformat(), (now + timedelta(days=1)).isoformat())
    by_day = _aggregate_by_day(rows)

    today_str = _day_str(now)
    today_totals = by_day.get(today_str, {})

    week_days = [_day_str(now - timedelta(days=i)) for i in range(6, -1, -1)]
    month_days = [_day_str(now - timedelta(days=i)) for i in range(29, -1, -1)]

    def series_for(days):
        return [
            {
                "id": cid,
                "label": CAT_META[cid]["label"],
                "color_light": CAT_META[cid]["color_light"],
                "color_dark": CAT_META[cid]["color_dark"],
                "data": [round(by_day.get(d, {}).get(cid, 0) / 60, 1) for d in days],
            }
            for cid in CAT_ORDER
        ]

    return {
        "generated_at": now.isoformat(),
        "today": {
            "date": today_str,
            "labels": [CAT_META[cid]["label"] for cid in CAT_ORDER],
            "colors_light": [CAT_META[cid]["color_light"] for cid in CAT_ORDER],
            "colors_dark": [CAT_META[cid]["color_dark"] for cid in CAT_ORDER],
            "minutes": [round(today_totals.get(cid, 0) / 60, 1) for cid in CAT_ORDER],
        },
        "week": {
            "day_labels": [datetime.strptime(d, "%Y-%m-%d").strftime("%a %d") for d in week_days],
            "series": series_for(week_days),
        },
        "month": {
            "day_labels": [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in month_days],
            "series": series_for(month_days),
        },
    }


def get_widget_data():
    """Simple per-category totals (minutes) for today / this week / this month -
    used by the floating widget's plain bar rows (no charting lib needed)."""
    now = datetime.now().astimezone()
    start_month = now - timedelta(days=30)
    start_week = now - timedelta(days=6)
    rows = db.fetch_range(start_month.isoformat(), (now + timedelta(days=1)).isoformat())

    today_str = _day_str(now)
    totals_today = {cid: 0 for cid in CAT_ORDER}
    totals_week = {cid: 0 for cid in CAT_ORDER}
    totals_month = {cid: 0 for cid in CAT_ORDER}

    for ts, interval_seconds, app, title, cat_id, conf in rows:
        dt = datetime.fromisoformat(ts)
        if cat_id not in totals_month:
            continue
        totals_month[cat_id] += interval_seconds
        if dt >= start_week:
            totals_week[cat_id] += interval_seconds
        if _day_str(dt) == today_str:
            totals_today[cat_id] += interval_seconds

    def as_minutes(totals):
        return [round(totals[cid] / 60, 1) for cid in CAT_ORDER]

    return {
        "generated_at": now.isoformat(),
        "labels": [CAT_META[cid]["label"] for cid in CAT_ORDER],
        "colors_light": [CAT_META[cid]["color_light"] for cid in CAT_ORDER],
        "colors_dark": [CAT_META[cid]["color_dark"] for cid in CAT_ORDER],
        "today_minutes": as_minutes(totals_today),
        "week_minutes": as_minutes(totals_week),
        "month_minutes": as_minutes(totals_month),
    }
