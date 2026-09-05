"""
timed_test.py (replaces timed_test.py + timed_test_selection.py)

Timer fix: the original `run_timer()` was a bare `while True: sleep(1)` loop
that runs *inside* a single Streamlit script execution — meaning the script
never reaches completion, so no other widget on the page (Next, Previous,
answer buttons) can ever be interacted with while the timer is "running".
It's replaced with an `st.fragment(run_every="1s")`, Streamlit's native
mechanism for a self-refreshing region that doesn't block the rest of the
page.

The duration selector also drops the unused `streamlit_extras` dependency
(timed_test_selection.py) in favour of the built-in `st.segmented_control`.
"""

from datetime import datetime
import random

import streamlit as st

import theme
import utils
from components import render_filter_sidebar, render_empty_state, render_results_dashboard
from config import PLAY_RESULT_KEYS, TIMER_KEYS, reset_keys
from database import filter_papers
from feedback import render_answer_options
from linked_list import DoublyLinkedList

DURATION_PRESETS = {"5 min": 5, "10 min": 10, "20 min": 20, "30 min": 30, "60 min": 60}


@st.fragment(run_every="1s")
def _render_timer(total_seconds: int):
    if st.session_state.get("finished_test"):
        st.metric("⏳ Time Remaining", "00:00")
        return

    elapsed = (datetime.now() - st.session_state.timer_start).total_seconds()
    remaining = max(total_seconds - int(elapsed), 0)
    minutes, seconds = divmod(remaining, 60)
    st.metric("⏳ Time Remaining", f"{minutes:02d}:{seconds:02d}")

    if remaining <= 0 and not st.session_state.get("time_up"):
        st.session_state.time_up = True
        st.session_state.finished_test = True
        st.rerun()


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()

    st.title("⏱️ Timed Test")
    st.write("👾 Set a duration, answer as many as you can, review your score at the end.")

    with st.sidebar:
        st.header("⏱️ Test Duration")
        preset_label = st.segmented_control("Duration", list(DURATION_PRESETS.keys()), default="10 min", key="duration_preset")
        duration_minutes = DURATION_PRESETS.get(preset_label, 10)
        num_questions = st.number_input("Number of questions", min_value=1, value=10, step=1, key="num_questions")

    selections = render_filter_sidebar(quiz_mode=True, include_paper_selectors=False)

    st.subheader("🔍 Filtered Results")

    if st.button("Start Test", type="primary", disabled=not selections["subject"], key="generate_papers_button"):
        reset_keys(PLAY_RESULT_KEYS, TIMER_KEYS)
        filters = dict(selections["sql_filters"])
        filters["Paper_number"] = 1

        with st.spinner("Loading questions…"):
            results = filter_papers(filters, limit=int(num_questions))

        if not results:
            render_empty_state("No questions matched those filters", "Try widening Topic or Year.", icon="🔍")
            return

        entries = [(r[11], r[2], r[12]) for r in results]
        random.shuffle(entries)

        dll = DoublyLinkedList.from_iterable(entries)
        st.session_state.paper_paths_list = dll
        st.session_state.current_node = dll.head
        st.session_state.current_answer = dll.head.data[2]
        st.session_state.timer_start = datetime.now()
        st.session_state.test_duration_seconds = duration_minutes * 60
        st.rerun()

    dll = st.session_state.get("paper_paths_list")
    if not dll:
        render_empty_state("No test started yet", "Choose a subject, duration, and question count, then hit **Start Test**.", icon="⏱️")
        return

    timer_slot = st.empty()
    with timer_slot.container():
        _render_timer(st.session_state.get("test_duration_seconds", duration_minutes * 60))

    finished = st.session_state.get("finished_test", False)

    utils.add_divider(1)

    if finished:
        render_results_dashboard(
            st.session_state.get("correct_count", 0),
            st.session_state.get("wrong_count", 0),
            st.session_state.get("attempt_log", []),
        )
        if st.button("🔁 Start a new test", type="primary"):
            reset_keys(PLAY_RESULT_KEYS, TIMER_KEYS)
            st.rerun()
        return

    if "current_node" not in st.session_state or not st.session_state.current_node:
        st.session_state.current_node = dll.head

    node = st.session_state.current_node
    pdf_path, topic, correct_answer = node.data
    st.session_state.current_answer = correct_answer

    utils.render_pdf(pdf_path, empty_message="This question's PDF is missing from disk.")
    utils.add_divider(1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Previous", use_container_width=True, disabled=node.prev is None, key="previous_button"):
            st.session_state.current_node = dll.get_previous(node)
            st.rerun()
    with col2:
        if st.button("Next ➡", use_container_width=True, disabled=node.next is None, key="next_button"):
            st.session_state.current_node = dll.get_next(node)
            st.rerun()

    st.write("**Choose your answer:**")
    render_answer_options(mode="test", topic=topic)


render()
