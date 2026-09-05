"""
feedback.py  (replaces animations.py, and the options_quiz/options_test
helpers that used to live in display.py)

Two behavioural fixes beyond the visual refresh:

1. The original app let you click A/B/C/D repeatedly on the same question
   and incremented the correct/wrong counters every single time. Answers
   are now locked once a question has been answered (tracked per node id),
   so a Timed Test score can't be inflated by spam-clicking.
2. Feedback is a toast (st.toast) instead of a full markdown block — it
   doesn't push the rest of the page down and disappears on its own.
"""

from __future__ import annotations

import streamlit as st

OPTIONS = ["A", "B", "C", "D"]


def _node_key() -> str | None:
    node = st.session_state.get("current_node")
    return str(id(node)) if node else None


def render_answer_options(mode: str = "quiz", topic: str | None = None) -> None:
    """mode: 'quiz' shows instant right/wrong toast + balloons.
    mode: 'test' silently tallies correct/wrong for a results summary."""
    st.session_state.setdefault("correct_count", 0)
    st.session_state.setdefault("wrong_count", 0)
    st.session_state.setdefault("attempt_log", [])
    st.session_state.setdefault("answered_nodes", set())

    node_key = _node_key()
    already_answered = node_key in st.session_state.answered_nodes if node_key else False
    correct_answer = st.session_state.get("current_answer")

    cols = st.columns(4)
    for col, label in zip(cols, OPTIONS):
        with col:
            clicked = st.button(
                label,
                key=f"answer_{label.lower()}",
                use_container_width=True,
                disabled=already_answered,
            )
        if clicked and not already_answered and node_key:
            is_correct = label == correct_answer
            st.session_state.answered_nodes.add(node_key)
            if is_correct:
                st.session_state.correct_count += 1
            else:
                st.session_state.wrong_count += 1
            st.session_state.attempt_log.append({"topic": topic, "is_correct": is_correct})

            if mode == "quiz":
                if is_correct:
                    st.toast("Correct! Nice work. 🎉", icon="✅")
                    st.balloons()
                else:
                    st.toast(f"Not quite — the answer was {correct_answer}.", icon="❌")
            st.rerun()

    if already_answered:
        st.caption(f"✅ Answered — correct option was **{correct_answer}**. Use Next to continue.")


def render_live_scoreboard() -> None:
    correct = st.session_state.get("correct_count", 0)
    wrong = st.session_state.get("wrong_count", 0)
    c1, c2 = st.columns(2)
    c1.metric("✅ Correct", correct)
    c2.metric("❌ Incorrect", wrong)
