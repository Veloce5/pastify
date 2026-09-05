"""
database.py  (replaces filter_logic.py)

Every read is wrapped in st.cache_data so re-rendering a page (which happens
on every widget interaction in Streamlit) doesn't re-hit SQLite for data
that hasn't changed. The connection itself is a single cached resource
shared across the whole app session.

The eight near-identical `get_X` functions from the original filter_logic.py
have been collapsed into one generic, parameterized `get_distinct_values`.
"""

from __future__ import annotations

import sqlite3

import streamlit as st

from config import DB_PATH, resolve_media_path


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    """A single shared, cached SQLite connection for the app's lifetime."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA query_only = ON;")  # this app never writes to the DB
    return conn


# ---------------------------------------------------------------------------
# Generic cached query helpers
# ---------------------------------------------------------------------------
def _normalize(filters: dict | None) -> dict:
    """Drop empty filter values so cache keys stay stable and queries stay lean."""
    if not filters:
        return {}
    return {k: v for k, v in filters.items() if v}


@st.cache_data(show_spinner=False, ttl=3600)
def get_distinct_values(column: str, filters: dict | None = None) -> list:
    """Distinct values for `column`, restricted by an optional filter dict.

    filters: {"Subject_name": "Physics", "Year": [2022, 2023], ...}
    A list value becomes a SQL IN(...) clause; a scalar becomes `= ?`.
    """
    filters = _normalize(filters)
    conn = get_connection()

    query = f"SELECT DISTINCT {column} FROM past_papers WHERE Question IS NOT NULL"
    params: list = []

    for key, value in filters.items():
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            query += f" AND {key} IN ({','.join(['?'] * len(values))})"
            params.extend(values)
        else:
            query += f" AND {key} = ?"
            params.append(value)

    rows = conn.execute(query, params).fetchall()
    return [r[0] for r in rows]


@st.cache_data(show_spinner=False, ttl=3600)
def filter_papers(filters: dict, limit: int | None = None) -> list[tuple]:
    """Full-row query for the given filters. Optionally randomized + limited
    (used by Quiz / Timed Test which want a random subset)."""
    filters = _normalize(filters)
    conn = get_connection()

    query = "SELECT * FROM past_papers WHERE Question IS NOT NULL"
    params: list = []

    for key, value in filters.items():
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            query += f" AND {key} IN ({','.join(['?'] * len(values))})"
            params.extend(values)
        else:
            query += f" AND {key} = ?"
            params.append(value)

    if limit:
        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)

    return conn.execute(query, params).fetchall()


@st.cache_data(show_spinner=False, ttl=3600)
def get_subjects() -> list:
    return get_distinct_values("Subject_name")


@st.cache_data(show_spinner=False, ttl=3600)
def get_quiz_ready_subjects() -> list:
    """Subjects that have single-question papers with a letter answer (A-D) —
    i.e. subjects that are playable in Quiz Mode / Timed Test."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT Subject_name FROM past_papers
        WHERE Paper_number = 1 AND Answer IN ('A', 'B', 'C', 'D')
        """
    ).fetchall()
    return [r[0] for r in rows]


@st.cache_data(show_spinner=False, ttl=3600)
def get_subject_code(subject: str) -> str | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT Subject_code FROM past_papers WHERE Subject_name = ? LIMIT 1",
        (subject,),
    ).fetchone()
    return row[0] if row else None


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_paper_details(file_path: str) -> dict | None:
    """`file_path` is the DB-stored relative path (e.g.
    'qp/9618/2024/May_June/12/1(a).pdf') — it's used here purely as a
    lookup key, matching what's now stored in the Question column post
    clean_db.py. It is NOT resolved to a filesystem path in this function;
    that only happens at the point of actually reading the PDF bytes (see
    utils.get_pdf_page_images / utils.merge_pdfs), via
    config.resolve_media_path()."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT Subject_code, Paper_variant, Variant, Year, Question_Number
        FROM past_papers WHERE Question = ?
        """,
        (file_path,),
    ).fetchone()
    if not row:
        return None
    keys = ["subject_code", "paper_variant", "variant", "year", "question_number"]
    return dict(zip(keys, row))


def resolve_path(relative_path: str | None):
    """Thin re-export of config.resolve_media_path so callers that are
    already importing `database` for everything else don't need a second
    import just for path resolution."""
    return resolve_media_path(relative_path)


def media_exists(relative_path: str | None) -> bool:
    """True if the relative path stored in the DB actually resolves to a
    real file on this machine. Use this before ever handing a path to
    fitz/PdfMerger — replaces any old os.path.exists() call on a raw,
    possibly-absolute-Windows-style string."""
    resolved = resolve_media_path(relative_path)
    return resolved is not None and resolved.exists()


@st.cache_data(show_spinner=False, ttl=3600)
def get_sorted_topics(subject: str) -> tuple[list, list]:
    """Split topics into ('Chpt - N - Name' style, sorted by N) and the rest."""
    topics = get_distinct_values("Topic", {"Subject_name": subject})
    sorted_topics, unsorted_topics = [], []
    for topic in topics:
        parts = topic.split(" - ")
        if len(parts) >= 3:
            try:
                int(parts[1])
                sorted_topics.append(topic)
                continue
            except ValueError:
                pass
        unsorted_topics.append(topic)
    sorted_topics.sort(key=lambda t: int(t.split(" - ")[1]))
    return sorted_topics, sorted(unsorted_topics)
