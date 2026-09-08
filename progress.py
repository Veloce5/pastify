"""
progress.py

Pastify has no user accounts, so "who is this progress for" is answered by
a self-chosen profile name (see profile.py) rather than real auth. Anyone
using the same profile name on the same deployment shares history — that's
an acceptable trade-off for a single-tenant / classroom deployment, but
flagged here explicitly rather than silently pretended away. Swap this
layer for a real per-user store if you deploy this multi-tenant publicly.

Storage is a tiny local SQLite file (config.PROGRESS_DB_PATH), completely
separate from the read-only past_papers.db — we never want app logic that
mutates data anywhere near the past-paper catalogue itself.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

from config import (
    PROGRESS_DB_PATH,
    BADGE_ACCURACY_THRESHOLDS,
    BADGE_VOLUME_THRESHOLDS,
    BADGE_STREAK_THRESHOLDS,
)


@st.cache_resource(show_spinner=False)
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PROGRESS_DB_PATH), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile TEXT NOT NULL,
            ts TEXT NOT NULL,
            subject TEXT,
            topic TEXT,
            question_number TEXT,
            is_correct INTEGER NOT NULL,
            time_taken_seconds REAL,
            mode TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_profile ON attempts(profile, ts)")
    conn.commit()
    return conn


def log_attempt(profile: str, subject: str | None, topic: str | None, question_number: str,
                 is_correct: bool, time_taken_seconds: float | None, mode: str) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO attempts (profile, ts, subject, topic, question_number, is_correct, time_taken_seconds, mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (profile, datetime.now().isoformat(timespec="seconds"), subject, topic,
         question_number, int(is_correct), time_taken_seconds, mode),
    )
    conn.commit()


def get_history(profile: str, subject: str | None = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT ts, subject, topic, question_number, is_correct, time_taken_seconds, mode FROM attempts WHERE profile = ?"
    params: list = [profile]
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    query += " ORDER BY ts ASC"
    rows = conn.execute(query, params).fetchall()
    keys = ["ts", "subject", "topic", "question_number", "is_correct", "time_taken_seconds", "mode"]
    return [dict(zip(keys, r)) for r in rows]


def compute_streak(profile: str) -> dict:
    """Consecutive-day streak based on calendar dates with >=1 attempt.
    Returns {"current": int, "longest": int, "active_today": bool}."""
    history = get_history(profile)
    if not history:
        return {"current": 0, "longest": 0, "active_today": False}

    days = sorted({datetime.fromisoformat(h["ts"]).date() for h in history})
    longest = current = 1
    for i in range(1, len(days)):
        if days[i] - days[i - 1] == timedelta(days=1):
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    longest = max(longest, current)

    today = date.today()
    active_today = days[-1] == today
    # Current streak (as of today) is only "current" if the most recent
    # active day is today or yesterday — otherwise it's broken.
    if days[-1] not in (today, today - timedelta(days=1)):
        current_streak = 0
    else:
        current_streak = current

    return {"current": current_streak, "longest": longest, "active_today": active_today}


def compute_badges(profile: str) -> list[dict]:
    """Rule-based badges — simple, transparent thresholds rather than a
    hidden scoring model. Returns a list of {"name", "description", "earned"}."""
    history = get_history(profile)
    total = len(history)
    correct = sum(h["is_correct"] for h in history)
    accuracy = (correct / total) if total else 0.0
    streak = compute_streak(profile)

    badges = []
    for name, threshold in BADGE_VOLUME_THRESHOLDS.items():
        badges.append({
            "name": name,
            "description": f"Answer {threshold}+ questions",
            "earned": total >= threshold,
        })
    for name, threshold in BADGE_ACCURACY_THRESHOLDS.items():
        badges.append({
            "name": name,
            "description": f"{int(threshold * 100)}%+ accuracy over 20+ questions",
            "earned": total >= 20 and accuracy >= threshold,
        })
    for name, threshold in BADGE_STREAK_THRESHOLDS.items():
        badges.append({
            "name": name,
            "description": f"{threshold}+ consecutive days of practice",
            "earned": streak["longest"] >= threshold,
        })
    return badges


def get_topic_accuracy(profile: str, subject: str | None = None) -> dict[str, dict]:
    """{topic: {"correct": n, "total": n, "accuracy": pct}} for a heatmap."""
    history = get_history(profile, subject=subject)
    by_topic: dict[str, dict] = {}
    for h in history:
        topic = h["topic"] or "Unspecified"
        bucket = by_topic.setdefault(topic, {"correct": 0, "total": 0})
        bucket["total"] += 1
        bucket["correct"] += h["is_correct"]
    for bucket in by_topic.values():
        bucket["accuracy"] = bucket["correct"] / bucket["total"] if bucket["total"] else 0.0
    return by_topic


def get_daily_activity(profile: str, days: int = 30) -> dict[str, int]:
    """{'YYYY-MM-DD': attempt_count} for the last `days` days, zero-filled."""
    history = get_history(profile)
    cutoff = date.today() - timedelta(days=days)
    counts: dict[str, int] = {(cutoff + timedelta(days=i)).isoformat(): 0 for i in range(days + 1)}
    for h in history:
        d = datetime.fromisoformat(h["ts"]).date()
        if d >= cutoff:
            counts[d.isoformat()] = counts.get(d.isoformat(), 0) + 1
    return counts
