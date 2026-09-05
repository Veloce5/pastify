"""
components.py

The single biggest source of duplication in the original app was the
cascading sidebar filter block (Subject -> Topic -> Subtopic -> Year ->
Variant -> Paper Number -> Paper Variant -> Difficulty), which was
copy-pasted near-verbatim into app.py, quiz.py, worksheet.py and
timed_test.py. It now lives here once, parameterized by which stages a
given page actually needs.
"""

from __future__ import annotations

import streamlit as st

import utils
from config import FILTER_KEYS, BROWSE_RESULT_KEYS, PLAY_RESULT_KEYS, reset_keys
from database import (
    get_subjects,
    get_quiz_ready_subjects,
    get_subject_code,
    get_distinct_values,
    fetch_paper_details,
)


# ---------------------------------------------------------------------------
# Filter sidebar
# ---------------------------------------------------------------------------
def render_filter_sidebar(quiz_mode: bool = False, include_paper_selectors: bool = True) -> dict:
    """Renders the full cascading filter UI in the sidebar and returns both
    the raw selections and a ready-to-use SQL filter dict.

    Returns
    -------
    dict with keys: subject, subject_code, topics, subtopics, years,
    variants, paper_numbers, paper_variants, difficulties, sql_filters
    """
    with st.sidebar:
        st.header("🖍️ Filter Options")

        if st.button("↺ Reset Filters", use_container_width=True, key="reset_filters_btn"):
            reset_keys(FILTER_KEYS, BROWSE_RESULT_KEYS, PLAY_RESULT_KEYS)
            st.rerun()

        subject_list = get_quiz_ready_subjects() if quiz_mode else get_subjects()
        selected_subject = st.selectbox(
            "Subject",
            subject_list,
            index=None,
            key="subject_select",
            help="Select the subject to filter past papers.",
            placeholder="Choose a subject…",
        )

        selections = {
            "subject": selected_subject,
            "subject_code": get_subject_code(selected_subject) if selected_subject else None,
            "topics": [], "subtopics": [], "years": [], "variants": [],
            "paper_numbers": [], "paper_variants": [], "difficulties": [],
        }

        if not selected_subject:
            st.caption("👆 Pick a subject to reveal more filters.")
            selections["sql_filters"] = {}
            return selections

        with st.expander("📂 Topic & Subtopic", expanded=False):
            sorted_topics, unsorted_topics = utils.get_sorted_topics(selected_subject)
            all_topics = sorted_topics + unsorted_topics
            select_all_topics = st.checkbox("Select all topics", key="all_topics")
            selections["topics"] = st.multiselect(
                "Topics", all_topics,
                default=all_topics if select_all_topics else [],
                key="topics_multiselect",
            )
            if selections["topics"]:
                subtopics, _ = utils.get_sorted_subtopics(selected_subject, selections["topics"])
                select_all_sub = st.checkbox("Select all subtopics", key="all_subtopics")
                selections["subtopics"] = st.multiselect(
                    "Subtopics", subtopics,
                    default=subtopics if select_all_sub else [],
                    key="subtopics_multiselect",
                )

        with st.expander("📅 Year & Variant", expanded=False):
            years = get_distinct_values("Year", {
                "Subject_name": selected_subject, "Topic": selections["topics"], "Sub_topic": selections["subtopics"],
            })
            select_all_years = st.checkbox("Select all years", key="all_years")
            selections["years"] = st.multiselect(
                "Years", sorted(years, reverse=True),
                default=years if select_all_years else [],
                key="years_multiselect",
            )
            if selections["years"]:
                variants = get_distinct_values("Variant", {
                    "Subject_name": selected_subject, "Year": selections["years"],
                    "Topic": selections["topics"], "Sub_topic": selections["subtopics"],
                })
                select_all_variants = st.checkbox("Select all variants", key="all_variants")
                selections["variants"] = st.multiselect(
                    "Variants", variants,
                    default=variants if select_all_variants else [],
                    key="variants_multiselect",
                )

        if include_paper_selectors:
            with st.expander("📄 Paper Number & Variant", expanded=False):
                if selections["variants"]:
                    paper_numbers = get_distinct_values("Paper_number", {
                        "Subject_name": selected_subject, "Year": selections["years"],
                        "Variant": selections["variants"], "Topic": selections["topics"],
                        "Sub_topic": selections["subtopics"],
                    })
                    select_all_pn = st.checkbox("Select all paper numbers", key="all_paper_numbers")
                    selections["paper_numbers"] = st.multiselect(
                        "Paper Numbers", paper_numbers,
                        default=paper_numbers if select_all_pn else [],
                        key="paper_numbers_multiselect",
                    )
                    if selections["paper_numbers"]:
                        paper_variants = get_distinct_values("Paper_variant", {
                            "Subject_name": selected_subject, "Year": selections["years"],
                            "Variant": selections["variants"], "Paper_number": selections["paper_numbers"],
                            "Topic": selections["topics"], "Sub_topic": selections["subtopics"],
                        })
                        select_all_pv = st.checkbox("Select all paper variants", key="all_paper_variants")
                        selections["paper_variants"] = st.multiselect(
                            "Paper Variants", paper_variants,
                            default=paper_variants if select_all_pv else [],
                            key="paper_variants_multiselect",
                        )
                else:
                    st.caption("Select a variant above first.")

        with st.expander("🎚️ Difficulty", expanded=False):
            ready = selections["paper_variants"] if include_paper_selectors else selections["years"]
            if ready:
                difficulties = get_distinct_values("Difficulty", {
                    "Subject_name": selected_subject, "Year": selections["years"],
                    "Variant": selections["variants"], "Paper_number": selections["paper_numbers"],
                    "Paper_variant": selections["paper_variants"], "Topic": selections["topics"],
                    "Sub_topic": selections["subtopics"],
                })
                select_all_diff = st.checkbox("Select all difficulties", key="all_difficulties")
                selections["difficulties"] = st.multiselect(
                    "Difficulty Levels", difficulties,
                    default=difficulties if select_all_diff else [],
                    key="difficulties_multiselect",
                )
            else:
                st.caption("Keep narrowing filters above first.")

    selections["sql_filters"] = {
        "Subject_name": selected_subject,
        "Topic": selections["topics"],
        "Sub_topic": selections["subtopics"],
        "Year": selections["years"],
        "Variant": selections["variants"],
        "Paper_number": selections["paper_numbers"],
        "Paper_variant": selections["paper_variants"],
        "Difficulty": selections["difficulties"],
    }
    return selections


# ---------------------------------------------------------------------------
# Empty / status states
# ---------------------------------------------------------------------------
def render_empty_state(title: str, subtitle: str, icon: str = "🗂️") -> None:
    st.markdown(
        f"""
        <div style="text-align:center; padding: 3rem 1rem; border: 1px dashed var(--border-color, rgba(128,128,128,.25));
                    border-radius: 12px; margin: 1rem 0;">
            <div style="font-size: 2.5rem;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; margin-top: .5rem;">{title}</div>
            <div style="opacity: .7; margin-top: .25rem;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Paper detail card (metrics + copy-paste snippet)
# ---------------------------------------------------------------------------
def render_paper_detail_card(pdf_path: str | None) -> None:
    if not pdf_path:
        return
    details = fetch_paper_details(pdf_path)
    if not details:
        st.warning("Couldn't fetch metadata for this paper.")
        return

    utils.add_divider(1)
    cols = st.columns(5)
    labels = [
        ("Subject Code", details["subject_code"]),
        ("Year", details["year"]),
        ("Variant", details["variant"]),
        ("Paper Variant", details["paper_variant"]),
        ("Question No.", details["question_number"]),
    ]
    for col, (label, value) in zip(cols, labels):
        col.metric(label, value)

    mapping = utils.get_mapping(details["variant"])
    snippet = utils.generate_snippet(details["subject_code"], details["paper_variant"], mapping, details["year"])
    st.code(snippet, language="text")


# ---------------------------------------------------------------------------
# Results dashboard (Quiz / Timed Test)
# ---------------------------------------------------------------------------
def render_results_dashboard(correct: int, wrong: int, attempt_log: list[dict] | None = None) -> None:
    total = correct + wrong
    accuracy = (correct / total * 100) if total else 0.0

    st.subheader("📊 Your Results")
    c1, c2, c3 = st.columns(3)
    c1.metric("Correct", correct)
    c2.metric("Incorrect", wrong)
    c3.metric("Accuracy", f"{accuracy:.0f}%")

    if total == 0:
        render_empty_state("No attempts yet", "Answer a few questions to see your stats here.", icon="📈")
        return

    st.progress(min(max(accuracy / 100, 0.0), 1.0))

    if attempt_log:
        by_topic: dict[str, dict[str, int]] = {}
        for entry in attempt_log:
            topic = entry.get("topic") or "Unspecified"
            bucket = by_topic.setdefault(topic, {"correct": 0, "wrong": 0})
            bucket["correct" if entry["is_correct"] else "wrong"] += 1

        if by_topic:
            st.caption("Accuracy by topic")
            chart_data = {
                topic: round(stats["correct"] / (stats["correct"] + stats["wrong"]) * 100)
                for topic, stats in by_topic.items()
            }
            st.bar_chart(chart_data)
