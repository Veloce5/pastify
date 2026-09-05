"""worksheet.py — build a merged, shuffled worksheet PDF (question set + answer key)."""

import random

import streamlit as st

import theme
import utils
from components import render_filter_sidebar, render_empty_state
from database import filter_papers


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()

    st.title("📝 Worksheet Builder")
    st.write("Generate a merged, shuffled worksheet (with a matching answer key) from your filtered papers.")

    selections = render_filter_sidebar(quiz_mode=False, include_paper_selectors=True)

    st.subheader("🔍 Filtered Results")

    if st.button("Generate Worksheet", type="primary", disabled=not selections["subject"], key="generate_worksheet_button"):
        with st.spinner("Finding matching questions…"):
            results = filter_papers(selections["sql_filters"])

        if not results:
            render_empty_state(
                "No papers matched those filters",
                "Try widening your Year range or clearing the Difficulty filter.",
                icon="🔍",
            )
            return

        st.success(f"Found {len(results)} questions matching your criteria.")
        questions = [r[11] for r in results]
        answers = [r[12] for r in results]
        paired = list(zip(questions, answers))
        random.shuffle(paired)
        questions, answers = zip(*paired)

        progress = st.progress(0, text="Merging PDFs…")
        q_bytes, a_bytes = utils.merge_pdfs(list(questions), list(answers), progress_bar=progress)
        progress.empty()

        if q_bytes and a_bytes:
            zip_buffer = utils.create_zip({
                "worksheet_questions.pdf": q_bytes,
                "worksheet_answers.pdf": a_bytes,
            })
            st.session_state.worksheet_zip = zip_buffer.getvalue()
            st.session_state.worksheet_count = len(results)
        else:
            st.error("Something went wrong while merging. Please try again.")

    if st.session_state.get("worksheet_zip"):
        utils.add_divider(1)
        st.success(f"✅ Worksheet ready — {st.session_state.worksheet_count} questions.")
        st.download_button(
            "⬇️ Download Worksheet + Answer Key (.zip)",
            data=st.session_state.worksheet_zip,
            file_name="pastify_worksheet.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )


render()
