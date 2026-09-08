"""
worksheet.py — Smart Worksheet Builder.

New flow: filtered results get added to a persistent "cart" (session_state)
rather than being merged immediately. You can keep browsing and adding
from different filter combinations, review the whole set, then confirm and
generate in one shot via an st.dialog — so a misclick doesn't kick off an
expensive merge of the wrong 80 questions.
"""

import streamlit as st

import theme
import utils
from components import render_filter_sidebar, render_empty_state, render_cart_summary, add_paper_to_cart
from config import CART_KEYS, reset_keys
from database import filter_papers
from profile import render_profile_badge


@st.dialog("Generate worksheet?")
def _confirm_and_generate(cart: list[dict]):
    st.write(f"This will merge **{len(cart)} question(s)** into a question booklet and a matching answer key.")
    st.caption("Files missing on disk will be skipped automatically rather than failing the whole export.")

    if st.button("Generate now", type="primary", use_container_width=True):
        questions = [item["question_path"] for item in cart]
        answers = [item["answer_path"] for item in cart]

        progress_bar = st.progress(0, text="Merging PDFs…")
        q_bytes, a_bytes = utils.merge_pdfs(questions, answers, progress_bar=progress_bar)
        progress_bar.empty()

        if q_bytes and a_bytes:
            zip_buffer = utils.create_zip({
                "worksheet_questions.pdf": q_bytes,
                "worksheet_answers.pdf": a_bytes,
            })
            st.session_state.worksheet_zip = zip_buffer.getvalue()
            st.session_state.worksheet_count = len(cart)
            st.rerun()
        else:
            st.error("Something went wrong while merging. Please try again.")

    if st.button("Cancel", use_container_width=True):
        st.rerun()


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("📝 Worksheet Builder")
    st.write("Filter, add questions to your cart, then generate one merged worksheet + answer key whenever you're ready.")

    selections = render_filter_sidebar(quiz_mode=False, include_paper_selectors=True)

    st.subheader("🔍 Filtered Results")
    left, right = st.columns([2, 1])

    with left:
        if st.button("Add all matching to cart", type="primary", disabled=not selections["subject"], key="add_all_to_cart"):
            with st.spinner("Finding matching questions…"):
                results = filter_papers(selections["sql_filters"])
            if not results:
                render_empty_state("No papers matched those filters", "Try widening your filters.", icon="🔍")
            else:
                added = 0
                for r in results:
                    label = f"{r[1]} · {r[8]} · Q{r[10]}"  # Subject_code, Year, Question_Number
                    if add_paper_to_cart(r[11], r[12], label):
                        added += 1
                st.toast(f"Added {added} question(s) to your cart ({len(results) - added} already in it).", icon="🛒")

    with right:
        if st.button("Clear cart", use_container_width=True):
            reset_keys(CART_KEYS)
            st.rerun()

    st.divider()
    st.subheader("🛒 Your Worksheet Cart")
    cart = render_cart_summary()

    if cart:
        if st.button(f"Generate Worksheet ({len(cart)} questions)", type="primary", use_container_width=True):
            _confirm_and_generate(cart)

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
