"""
database.py

Cached, indexed, generic query layer over past_papers.db. Every read goes
through st.cache_data so re-rendering a page (which Streamlit does on
almost every widget interaction) never re-hits SQLite for data that hasn't
changed. The connection is a single cached resource for the whole app
session, and has its indexes bootstrapped exactly once (see config.ensure_indexes).
"""

from __future__ import annotations

import sqlite3

import streamlit as st

from config import DB_PATH, ensure_indexes, resolve_media_path


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    ensure_indexes(conn)  # no-op after the first run — CREATE INDEX IF NOT EXISTS
    conn.execute("PRAGMA query_only = ON;")  # this app never writes to past_papers.db
    return conn


# ---------------------------------------------------------------------------
# Generic cached query helpers
# ---------------------------------------------------------------------------
def _normalize(filters: dict | None) -> dict:
    if not filters:
        return {}
    return {k: v for k, v in filters.items() if v}


def _where_clause(filters: dict) -> tuple[str, list]:
    clauses, params = [], []
    for key, value in filters.items():
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            clauses.append(f"{key} IN ({','.join(['?'] * len(values))})")
            params.extend(values)
        else:
            clauses.append(f"{key} = ?")
            params.append(value)
    return (" AND " + " AND ".join(clauses)) if clauses else "", params

ALLOWED_COLUMNS = {
    "Subject_name", "Subject_code", "Topic", "Sub_topic", 
    "Year", "Variant", "Paper_number", "Paper_variant", "Difficulty"
}

@st.cache_data(show_spinner=False, ttl=3600)
def get_distinct_values(column: str, filters: dict = None) -> list:
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column requested: {column}")
    filters = _normalize(filters)
    conn = get_connection()
    where, params = _where_clause(filters)
    query = f"SELECT DISTINCT {column} FROM past_papers WHERE Question IS NOT NULL{where}"
    return [r[0] for r in conn.execute(query, params).fetchall()]


@st.cache_data(show_spinner=False, ttl=3600)
def filter_papers(filters: dict, limit: int | None = None) -> list[tuple]:
    filters = _normalize(filters)
    conn = get_connection()
    where, params = _where_clause(filters)
    query = f"SELECT * FROM past_papers WHERE Question IS NOT NULL{where}"
    if limit:
        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)
    return conn.execute(query, params).fetchall()


@st.cache_data(show_spinner=False, ttl=3600)
def get_subjects() -> list:
    return get_distinct_values("Subject_name")


@st.cache_data(show_spinner=False, ttl=3600)
def get_quiz_ready_subjects() -> list:
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
        "SELECT Subject_code FROM past_papers WHERE Subject_name = ? LIMIT 1", (subject,)
    ).fetchone()
    return row[0] if row else None


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_paper_details(file_path: str) -> dict | None:
    """`file_path` is the DB-stored relative path — used purely as a lookup
    key. Resolution to an actual filesystem path only happens in utils.py,
    right before a PDF is read."""
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


@st.cache_data(show_spinner=False, ttl=3600)
def get_sorted_topics(subject: str) -> tuple[list, list]:
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


# ---------------------------------------------------------------------------
# Dynamic keyword search — Topic / Sub_topic
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=600)
def search_topics(keyword: str, subject: str | None = None, limit: int = 50) -> list[dict]:
    """Free-text search across Topic and Sub_topic. Returns distinct
    (Subject_name, Topic, Sub_topic) triples matching the keyword, so the
    UI can offer "jump straight to this topic" results instead of forcing
    the user through the full cascade."""
    keyword = (keyword or "").strip()
    if len(keyword) < 2:
        return []

    conn = get_connection()
    like = f"%{keyword}%"
    query = """
        SELECT DISTINCT Subject_name, Topic, Sub_topic FROM past_papers
        WHERE (Topic LIKE ? OR Sub_topic LIKE ?) AND Question IS NOT NULL
    """
    params: list = [like, like]
    if subject:
        query += " AND Subject_name = ?"
        params.append(subject)
    query += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [{"subject": r[0], "topic": r[1], "sub_topic": r[2]} for r in rows]


def media_exists(relative_path: str | None) -> bool:
    resolved = resolve_media_path(relative_path)
    return resolved is not None and resolved.exists()


def resolve_path(relative_path: str | None):
    return resolve_media_path(relative_path)
