"""
config.py

Single source of truth for paths, performance bootstrapping (DB indexes),
and the session-state key registries every "Reset" button in the app reads
from — so resets can never drift out of sync between pages again.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "past_papers.db"
PROGRESS_DB_PATH = APP_DIR / "progress.db"  # local attempt history / streaks / badges
CSS_PATH = APP_DIR / "styles.css"
LOGO_PATH = APP_DIR / "1280x720.png"

OUTPUT_DIR = APP_DIR / "output_questions"

_warned_missing_output_dir = False


def resolve_media_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
        
    try:
        resolved = (OUTPUT_DIR / relative_path).resolve(strict=False)
        # Security check: Ensure the final path is actually inside OUTPUT_DIR
        if not resolved.is_relative_to(OUTPUT_DIR):
            return None
        return resolved
    except (ValueError, RuntimeError):
        return None


# ---------------------------------------------------------------------------
# Performance: one-time index bootstrap
# ---------------------------------------------------------------------------
_INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_subject ON past_papers(Subject_name)",
    "CREATE INDEX IF NOT EXISTS idx_subject_code ON past_papers(Subject_code)",
    "CREATE INDEX IF NOT EXISTS idx_topic ON past_papers(Subject_name, Topic)",
    "CREATE INDEX IF NOT EXISTS idx_year ON past_papers(Subject_name, Year)",
    "CREATE INDEX IF NOT EXISTS idx_variant ON past_papers(Subject_name, Year, Variant)",
    "CREATE INDEX IF NOT EXISTS idx_paper ON past_papers(Subject_name, Year, Variant, Paper_number, Paper_variant)",
    "CREATE INDEX IF NOT EXISTS idx_question_path ON past_papers(Question)",
]


def ensure_indexes(conn: sqlite3.Connection) -> None:
    """Every filter cascade in this app WHEREs on some prefix of
    (Subject_name, Topic, Year, Variant, Paper_number, Paper_variant) — the
    original schema had zero indexes, so every one of those queries was a
    full table scan. Safe to call on every startup; CREATE INDEX IF NOT
    EXISTS is a no-op after the first run."""
    for stmt in _INDEX_STATEMENTS:
        conn.execute(stmt)
    conn.commit()


# ---------------------------------------------------------------------------
# Session-state key registries
# ---------------------------------------------------------------------------
FILTER_KEYS = [
    "subject_select", "topics_multiselect", "subtopics_multiselect",
    "years_multiselect", "variants_multiselect", "paper_numbers_multiselect",
    "paper_variants_multiselect", "difficulties_multiselect",
    "all_topics", "all_subtopics", "all_years", "all_variants",
    "all_paper_numbers", "all_paper_variants", "all_difficulties",
    "keyword_search",
]

BROWSE_RESULT_KEYS = [
    "question_paths_list", "answer_paths_list", "current_index", "show_question",
]

PLAY_RESULT_KEYS = [
    "paper_paths_list", "current_node", "current_answer", "user_feedback",
    "correct_count", "wrong_count", "attempt_log", "answered_nodes",
    "question_shown_at",
]

TIMER_KEYS = ["timer_start", "time_up", "finished_test"]

CART_KEYS = ["worksheet_cart", "worksheet_zip", "worksheet_count"]

ALL_RESETTABLE_KEYS = FILTER_KEYS + BROWSE_RESULT_KEYS + PLAY_RESULT_KEYS + TIMER_KEYS + CART_KEYS


def reset_keys(*key_groups) -> None:
    import streamlit as st
    for group in key_groups:
        for key in group:
            st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Misc settings
# ---------------------------------------------------------------------------
PDF_RENDER_ZOOM = 2.0

# Gamification thresholds
BADGE_ACCURACY_THRESHOLDS = {"Sharp Shooter": 0.90, "Reliable": 0.75}
BADGE_VOLUME_THRESHOLDS = {"Century Club": 100, "Half Century": 50, "Getting Started": 10}
BADGE_STREAK_THRESHOLDS = {"7-Day Streak": 7, "3-Day Streak": 3}
