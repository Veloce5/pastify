"""
timed_test.py

The timer runs in an st.fragment(run_every="1s") — Streamlit's native
self-refreshing region — instead of the blocking `while True: sleep(1)`
loop earlier versions of this app used, which froze every other button on
the page for the full duration of the test. Duration presets use
st.segmented_control instead of a bare number input.
"""

from datetime import datetime
import random

import streamlit as st

import theme
import utils
import progress
from components import render_filter_sidebar, render_empty_state, render_badge_shelf
from analytics import render_accuracy_heatmap, render_accuracy_donut
from config import PLAY_RESULT_KEYS, TIMER_KEYS, reset_keys
from database import filter_papers
from feedback import render_answer_options, mark_question_shown
from linked_list import DoublyLinkedList
from profile import current_profile, render_profile_badge

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
    profile = current_profile()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("⏱️ Timed Test")
    st.write("👾 Set a duration, answer as many as you can, review a full results dashboard at the end.")

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

        entries = [(r[11], r[2], r[12], r[10]) for r in results]  # (path, topic, answer, question_number)
        random.shuffle(entries)

        dll = DoublyLinkedList.from_iterable(entries)
        st.session_state.paper_paths_list = dll
        st.session_state.current_node = dll.head
        st.session_state.current_answer = dll.head.data[2]
        st.session_state.timer_start = datetime.now()
        st.session_state.test_duration_seconds = duration_minutes * 60
        mark_question_shown()
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
        correct = st.session_state.get("correct_count", 0)
        wrong = st.session_state.get("wrong_count", 0)
        total = correct + wrong

        st.subheader("📊 Test Complete — Your Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Correct", correct)
        c2.metric("Incorrect", wrong)
        c3.metric("Accuracy", f"{(correct/total*100) if total else 0:.0f}%")

        tab1, tab2 = st.tabs(["Accuracy by Topic", "Badges Unlocked"])
        with tab1:
            topic_acc = progress.get_topic_accuracy(profile, subject=selections.get("subject"))
            render_accuracy_heatmap(topic_acc)
            render_accuracy_donut(correct, wrong)
        with tab2:
            render_badge_shelf(progress.compute_badges(profile))

        if st.button("🔁 Start a new test", type="primary"):
            reset_keys(PLAY_RESULT_KEYS, TIMER_KEYS)
            st.rerun()
        return

    if "current_node" not in st.session_state or not st.session_state.current_node:
        st.session_state.current_node = dll.head

    node = st.session_state.current_node
    pdf_path, topic, correct_answer, _question_number = node.data
    st.session_state.current_answer = correct_answer

    utils.render_pdf(pdf_path, empty_message="This question's PDF is missing from disk.")
    utils.add_divider(1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Previous", width="stretch", disabled=node.prev is None, key="previous_button"):
            st.session_state.current_node = dll.get_previous(node)
            mark_question_shown()
            st.rerun()
    with col2:
        if st.button("Next ➡", width="stretch", disabled=node.next is None, key="next_button"):
            st.session_state.current_node = dll.get_next(node)
            mark_question_shown()
            st.rerun()

    st.write("**Choose your answer:**")
    render_answer_options(mode="test", topic=topic, subject=selections["subject"], profile=profile)


render()
