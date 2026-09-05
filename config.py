"""
config.py

Now that past_papers.db stores portable relative paths (run clean_db.py once
if you haven't), OUTPUT_DIR is the single place that knows where the actual
`output_questions/` media folder lives on whatever machine the app is
running on — your Mac today, a cloud volume tomorrow. Nothing else in the
codebase should ever hardcode a path or do string surgery on one; everything
resolves through `resolve_media_path()` below.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "past_papers.db"
CSS_PATH = APP_DIR / "styles.css"
LOGO_PATH = APP_DIR / "1280x720.png"

# The relative paths stored in Question/Answer are resolved against this.
# Override at deploy time with an env var if the media lives outside the
# app folder (e.g. a mounted volume or object-storage sync target):
#     OUTPUT_DIR = Path(os.environ.get("PASTIFY_OUTPUT_DIR", APP_DIR / "output_questions"))
OUTPUT_DIR = APP_DIR / "output_questions"

_warned_missing_output_dir = False  # module-level flag so we only warn once per process


def resolve_media_path(relative_path: str | None) -> Path | None:
    """The one function that turns a DB-stored relative path (e.g.
    'qp/9618/2024/May_June/12/1(a).pdf') into a real, absolute filesystem
    Path. Returns None for empty/NULL input (e.g. a quiz-mode letter
    answer, which isn't a path at all and should never reach this
    function's caller expecting a file).

    No string slicing, no `.find()`, no assumptions about the OS path
    separator — just a pure pathlib join against OUTPUT_DIR.
    """
    global _warned_missing_output_dir

    if not relative_path:
        return None

    if not OUTPUT_DIR.exists() and not _warned_missing_output_dir:
        import logging
        logging.warning(
            "OUTPUT_DIR does not exist: %s — every PDF lookup will report "
            "'missing from disk' until this folder is present.", OUTPUT_DIR,
        )
        _warned_missing_output_dir = True

    # PurePosixPath semantics: DB values always use "/" regardless of host
    # OS; Path(...) below adapts to the local OS correctly either way.
    return (OUTPUT_DIR / relative_path).resolve()


# ---------------------------------------------------------------------------
# Session-state key registries
# ---------------------------------------------------------------------------
FILTER_KEYS = [
    "subject_select",
    "topics_multiselect",
    "subtopics_multiselect",
    "years_multiselect",
    "variants_multiselect",
    "paper_numbers_multiselect",
    "paper_variants_multiselect",
    "difficulties_multiselect",
    "all_topics",
    "all_subtopics",
    "all_years",
    "all_variants",
    "all_paper_numbers",
    "all_paper_variants",
    "all_difficulties",
]

BROWSE_RESULT_KEYS = [
    "question_paths_list",
    "answer_paths_list",
    "current_index",
    "show_question",
]

PLAY_RESULT_KEYS = [
    "paper_paths_list",
    "current_node",
    "current_answer",
    "user_feedback",
    "correct_count",
    "wrong_count",
    "attempt_log",
    "answered_nodes",
]

TIMER_KEYS = [
    "timer_start",
    "time_up",
    "finished_test",
]

ALL_RESETTABLE_KEYS = FILTER_KEYS + BROWSE_RESULT_KEYS + PLAY_RESULT_KEYS + TIMER_KEYS


def reset_keys(*key_groups):
    """Delete every key in the given groups (lists of str) from session_state."""
    import streamlit as st

    for group in key_groups:
        for key in group:
            st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Misc display settings
# ---------------------------------------------------------------------------
PDF_RENDER_ZOOM = 2.0  # PyMuPDF zoom factor for question/answer rendering
