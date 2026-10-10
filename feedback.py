"""
feedback.py

The answer buttons are wrapped in @st.fragment: clicking A/B/C/D now only
reruns this small fragment, not the whole page — on the old version, every
click re-ran the entire script, which meant Streamlit re-executed (even if
cache-hit) the full PDF rendering pipeline and the whole sidebar filter
cascade just to register one button click. This is the single biggest
interaction-latency fix in this overhaul.

Two behavioural guarantees carried over from the previous version, still
enforced here:
1. Answers lock after the first click on a given question (tracked per
   node id) — you can't inflate a score by spam-clicking.
2. Every answer is logged to progress.db with how long it took, feeding
   the analytics dashboard and gamification badges.
"""

from __future__ import annotations

import time

import streamlit as st

import progress

OPTIONS = ["A", "B", "C", "D"]


def _node_key() -> str | None:
    node = st.session_state.get("current_node")
    return str(id(node)) if node else None


def mark_question_shown() -> None:
    """Call this whenever a NEW question becomes the current one (on
    Generate / Next / Previous) so time-per-question is measured from the
    moment the student actually sees it, not from app start."""
    st.session_state["question_shown_at"] = time.time()


@st.fragment
def render_answer_options(mode: str, topic: str | None, subject: str | None, profile: str) -> None:
    """mode: 'quiz' shows an instant right/wrong toast + balloons.
    mode: 'test' tallies silently for the end-of-test results dashboard."""
    st.session_state.setdefault("correct_count", 0)
    st.session_state.setdefault("wrong_count", 0)
    st.session_state.setdefault("attempt_log", [])
    st.session_state.setdefault("answered_nodes", set())

    node_key = _node_key()
    already_answered = node_key in st.session_state.answered_nodes if node_key else False
    correct_answer = st.session_state.get("current_answer")
    question_number = None
    node = st.session_state.get("current_node")
    if node is not None:
        try:
            question_number = node.data[3]  # (pdf_path, topic, correct_answer, question_number)
        except (IndexError, AttributeError):
            question_number = None

    cols = st.columns(4)
    for col, label in zip(cols, OPTIONS):
        with col:
            clicked = st.button(label, key=f"answer_{label.lower()}", width="stretch", disabled=already_answered)
        if clicked and not already_answered and node_key:
            is_correct = label == correct_answer
            shown_at = st.session_state.get("question_shown_at")
            elapsed = round(time.time() - shown_at, 1) if shown_at else None

            st.session_state.answered_nodes.add(node_key)
            if is_correct:
                st.session_state.correct_count += 1
            else:
                st.session_state.wrong_count += 1
            st.session_state.attempt_log.append({"topic": topic, "is_correct": is_correct, "time_taken": elapsed})

            progress.log_attempt(
                profile=profile, subject=subject, topic=topic,
                question_number=str(question_number), is_correct=is_correct,
                time_taken_seconds=elapsed, mode=mode,
            )

            if mode == "quiz":
                if is_correct:
                    st.toast("Correct! Nice work. 🎉", icon="✅")
                    st.balloons()
                else:
                    st.toast(f"Not quite — the answer was {correct_answer}.", icon="❌")
            st.rerun(scope="fragment")

    if already_answered:
        st.caption(f"✅ Answered — correct option was **{correct_answer}**. Use Next to continue.")

    c1, c2 = st.columns(2)
    c1.metric("✅ Correct", st.session_state.correct_count)
    c2.metric("❌ Incorrect", st.session_state.wrong_count)
