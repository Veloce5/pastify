"""browse.py — filter, page through, and cart past papers."""

import random

import streamlit as st

import theme
import utils
from components import render_filter_sidebar, render_empty_state, render_paper_detail_card, add_paper_to_cart
from config import BROWSE_RESULT_KEYS, reset_keys
from database import filter_papers
from profile import render_profile_badge


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("📚 Browse Papers")
    st.write("Filter past papers by subject, topic, year, and difficulty — then flip between question and answer.")

    selections = render_filter_sidebar(quiz_mode=False, include_paper_selectors=True)

    st.subheader("🔍 Filtered Results")

    if st.button("Generate Papers", type="primary", key="generate_papers_button", disabled=not selections["subject"]):
        reset_keys(BROWSE_RESULT_KEYS)
        with st.spinner("Finding matching papers…"):
            results = filter_papers(selections["sql_filters"])

        if results:
            st.success(f"Found {len(results)} papers matching your criteria.")
            questions = [r[11] for r in results]
            answers = [r[12] for r in results]
            paired = list(zip(questions, answers))
            random.shuffle(paired)
            questions, answers = zip(*paired)

            st.session_state.question_paths_list = list(questions)
            st.session_state.answer_paths_list = list(answers)
            st.session_state.current_index = 0
            st.session_state.show_question = True
        else:
            render_empty_state(
                "No papers matched those filters",
                "Try widening your Year range or clearing the Difficulty filter.",
                icon="🔍",
            )

    if st.session_state.get("question_paths_list"):
        idx = st.session_state.current_index
        total = len(st.session_state.question_paths_list)
        q_path = st.session_state.question_paths_list[idx]
        a_path = st.session_state.answer_paths_list[idx]
        show_q = st.session_state.get("show_question", True)

        utils.add_divider(1)
        top_l, top_r = st.columns([3, 1])
        top_l.caption(f"Paper {idx + 1} of {total}")
        with top_r:
            if st.button("🛒 Add to cart", width="stretch", key="add_to_cart_browse"):
                added = add_paper_to_cart(q_path, a_path, label=f"Question {idx + 1}")
                st.toast("Added to worksheet cart!" if added else "Already in your cart.", icon="🛒")

        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button(
                "🙈 Show Answer" if show_q else "📖 Show Question",
                width="stretch", key="show_answer_button",
            ):
                st.session_state.show_question = not show_q
                st.rerun()

        st.markdown(f"#### {'Question' if show_q else 'Answer'}")
        utils.render_pdf(q_path if show_q else a_path, empty_message="This PDF is missing from disk.")

        nav1, _, nav3 = st.columns([1, 3, 1])
        with nav1:
            if st.button("⬅ Previous", width="stretch", disabled=idx == 0, key="previous_button"):
                st.session_state.current_index -= 1
                st.session_state.show_question = True
                st.rerun()
        with nav3:
            if st.button("Next ➡", width="stretch", disabled=idx >= total - 1, key="next_button"):
                st.session_state.current_index += 1
                st.session_state.show_question = True
                st.rerun()

        render_paper_detail_card(q_path)
    else:
        render_empty_state(
            "No papers loaded yet",
            "Pick a subject in the sidebar and hit **Generate Papers** to get started.",
            icon="📚",
        )


render()
