"""quiz.py — untimed, instant-feedback single-question practice mode."""

import random

import streamlit as st

import theme
import utils
from components import render_filter_sidebar, render_empty_state
from config import PLAY_RESULT_KEYS, reset_keys
from database import filter_papers
from feedback import render_answer_options, mark_question_shown
from linked_list import DoublyLinkedList
from profile import current_profile, render_profile_badge


def render():
    theme.apply_page_theme()
    profile = current_profile()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("🎮 Quiz Mode")
    st.write("👾 Single questions, instant feedback. No pressure, no clock.")

    selections = render_filter_sidebar(quiz_mode=True, include_paper_selectors=False)

    st.subheader("🔍 Filtered Results")

    if st.button("Generate Quiz", type="primary", disabled=not selections["subject"], key="generate_papers_button"):
        reset_keys(PLAY_RESULT_KEYS)
        filters = dict(selections["sql_filters"])
        filters["Paper_number"] = 1  # quiz mode only uses single-question, letter-answer papers

        with st.spinner("Loading questions…"):
            results = filter_papers(filters)

        if not results:
            render_empty_state("No questions matched those filters", "Try widening Topic or Year.", icon="🔍")
            return

        st.success(f"Found {len(results)} questions. Shuffled and ready!")
        entries = [(r[11], r[2], r[12], r[10]) for r in results]  # (path, topic, answer, question_number)
        random.shuffle(entries)

        dll = DoublyLinkedList.from_iterable(entries)
        st.session_state.paper_paths_list = dll
        st.session_state.current_node = dll.head
        st.session_state.current_answer = dll.head.data[2]
        mark_question_shown()

    utils.add_divider(1)

    dll = st.session_state.get("paper_paths_list")
    if not dll:
        render_empty_state("No quiz loaded yet", "Pick a subject and hit **Generate Quiz** to start.", icon="🎮")
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
        if st.button("⬅ Previous", use_container_width=True, disabled=node.prev is None, key="previous_button"):
            st.session_state.current_node = dll.get_previous(node)
            mark_question_shown()
            st.rerun()
    with col2:
        if st.button("Next ➡", use_container_width=True, disabled=node.next is None, key="next_button"):
            st.session_state.current_node = dll.get_next(node)
            mark_question_shown()
            st.rerun()

    st.write("**Choose your answer:**")
    render_answer_options(mode="quiz", topic=topic, subject=selections["subject"], profile=profile)


render()
