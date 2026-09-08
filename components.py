"""
components.py

Shared UI building blocks. The filter panel is the big change here: the
old version was a flat stack of five nested `st.expander`s in the sidebar,
which got overwhelming fast on a filter chain this deep (Subject -> Topic
-> Subtopic -> Year -> Variant -> Paper Number -> Paper Variant ->
Difficulty). It's now: a keyword search box (jumps straight to matching
topics), a single always-visible Subject selector, and everything else
collapsed behind one `st.popover` with tabs — so the sidebar shows one
button instead of a wall of accordions, and power users still get the full
cascade one click away.
"""

from __future__ import annotations

import streamlit as st

import utils
from config import FILTER_KEYS, BROWSE_RESULT_KEYS, PLAY_RESULT_KEYS, reset_keys
from database import (
    get_subjects, get_quiz_ready_subjects, get_subject_code,
    get_distinct_values, fetch_paper_details, search_topics,
)


# ---------------------------------------------------------------------------
# Filter Panel Helpers (Refactored to reduce Cyclomatic Complexity)
# ---------------------------------------------------------------------------
def _render_keyword_search() -> None:
    keyword = st.text_input(
        "Search topics", key="keyword_search", placeholder="e.g. 'photosynthesis', 'binary trees'…",
        label_visibility="collapsed",
    )
    if keyword and len(keyword.strip()) >= 2:
        matches = search_topics(keyword)
        if matches:
            st.caption(f"{len(matches)} topic match(es):")
            for m in matches[:6]:
                label = f"{m['subject']} · {m['topic']}"
                if st.button(label, key=f"search_hit_{m['subject']}_{m['topic']}_{m['sub_topic']}", use_container_width=True):
                    st.session_state["subject_select"] = m["subject"]
                    st.session_state["_pending_topic"] = m["topic"]
                    st.rerun()
        else:
            st.caption("No topics match that search.")
        st.divider()


def _render_topic_tab(selected_subject: str, pending_topic: str | None) -> tuple[list, list]:
    sorted_topics, unsorted_topics = utils.get_sorted_topics(selected_subject)
    all_topics = sorted_topics + unsorted_topics
    default_topics = [pending_topic] if pending_topic in all_topics else []
    
    select_all_topics = st.checkbox("Select all topics", key="all_topics")
    topics = st.multiselect(
        "Topics", all_topics,
        default=all_topics if select_all_topics else default_topics,
        key="topics_multiselect",
    )
    
    subtopics = []
    if topics:
        sub_list, _ = utils.get_sorted_subtopics(selected_subject, topics)
        select_all_sub = st.checkbox("Select all subtopics", key="all_subtopics")
        subtopics = st.multiselect(
            "Subtopics", sub_list,
            default=sub_list if select_all_sub else [],
            key="subtopics_multiselect",
        )
    return topics, subtopics


def _render_year_variant_tab(selected_subject: str, topics: list, subtopics: list) -> tuple[list, list]:
    years_list = get_distinct_values("Year", {
        "Subject_name": selected_subject, "Topic": topics, "Sub_topic": subtopics,
    })
    
    select_all_years = st.checkbox("Select all years", key="all_years")
    years = st.multiselect(
        "Years", sorted(years_list, reverse=True),
        default=years_list if select_all_years else [],
        key="years_multiselect",
    )
    
    variants = []
    if years:
        var_list = get_distinct_values("Variant", {
            "Subject_name": selected_subject, "Year": years,
            "Topic": topics, "Sub_topic": subtopics,
        })
        select_all_variants = st.checkbox("Select all variants", key="all_variants")
        variants = st.multiselect(
            "Variants", var_list,
            default=var_list if select_all_variants else [],
            key="variants_multiselect",
        )
    return years, variants


def _render_paper_tab(selected_subject: str, topics: list, subtopics: list, years: list, variants: list) -> tuple[list, list]:
    paper_numbers = []
    paper_variants = []
    
    if variants:
        pn_list = get_distinct_values("Paper_number", {
            "Subject_name": selected_subject, "Year": years,
            "Variant": variants, "Topic": topics,
            "Sub_topic": subtopics,
        })
        select_all_pn = st.checkbox("Select all paper numbers", key="all_paper_numbers")
        paper_numbers = st.multiselect(
            "Paper Numbers", pn_list,
            default=pn_list if select_all_pn else [],
            key="paper_numbers_multiselect",
        )
        
        if paper_numbers:
            pv_list = get_distinct_values("Paper_variant", {
                "Subject_name": selected_subject, "Year": years,
                "Variant": variants, "Paper_number": paper_numbers,
                "Topic": topics, "Sub_topic": subtopics,
            })
            select_all_pv = st.checkbox("Select all paper variants", key="all_paper_variants")
            paper_variants = st.multiselect(
                "Paper Variants", pv_list,
                default=pv_list if select_all_pv else [],
                key="paper_variants_multiselect",
            )
    else:
        st.caption("Select a variant first.")
        
    return paper_numbers, paper_variants


def _render_difficulty_tab(selected_subject: str, topics: list, subtopics: list, years: list, variants: list, paper_numbers: list, paper_variants: list, is_ready: bool) -> list:
    difficulties = []
    if is_ready:
        diff_list = get_distinct_values("Difficulty", {
            "Subject_name": selected_subject, "Year": years,
            "Variant": variants, "Paper_number": paper_numbers,
            "Paper_variant": paper_variants, "Topic": topics,
            "Sub_topic": subtopics,
        })
        select_all_diff = st.checkbox("Select all difficulties", key="all_difficulties")
        difficulties = st.multiselect(
            "Difficulty Levels", diff_list,
            default=diff_list if select_all_diff else [],
            key="difficulties_multiselect",
        )
    else:
        st.caption("Keep narrowing the filters above first.")
    return difficulties


# ---------------------------------------------------------------------------
# Filter panel (Main Entry)
# ---------------------------------------------------------------------------
def render_filter_sidebar(quiz_mode: bool = False, include_paper_selectors: bool = True) -> dict:
    with st.sidebar:
        st.header("🔍 Find Papers")

        if st.button("↺ Reset Filters", use_container_width=True, key="reset_filters_btn"):
            reset_keys(FILTER_KEYS, BROWSE_RESULT_KEYS, PLAY_RESULT_KEYS)
            st.rerun()

        _render_keyword_search()

        # --- Primary selector (always visible) --------------------------
        subject_list = get_quiz_ready_subjects() if quiz_mode else get_subjects()
        selected_subject = st.selectbox(
            "Subject", subject_list, index=None, key="subject_select",
            placeholder="Choose a subject…",
        )

        selections = {
            "subject": selected_subject,
            "subject_code": get_subject_code(selected_subject) if selected_subject else None,
            "topics": [], "subtopics": [], "years": [], "variants": [],
            "paper_numbers": [], "paper_variants": [], "difficulties": [],
        }

        if not selected_subject:
            st.caption("👆 Pick a subject to unlock the rest of the filters.")
            selections["sql_filters"] = {}
            return selections

        # A topic jumped to from search gets pre-selected once, then cleared.
        pending_topic = st.session_state.pop("_pending_topic", None)

        with st.popover("⚙️ Advanced Filters", use_container_width=True):
            tab_labels = ["Topic", "Year & Variant"]
            if include_paper_selectors:
                tab_labels.append("Paper")
            tab_labels.append("Difficulty")
            tabs = st.tabs(tab_labels)
            tab_idx = 0

            with tabs[tab_idx]:
                selections["topics"], selections["subtopics"] = _render_topic_tab(selected_subject, pending_topic)
            tab_idx += 1

            with tabs[tab_idx]:
                selections["years"], selections["variants"] = _render_year_variant_tab(
                    selected_subject, selections["topics"], selections["subtopics"]
                )
            tab_idx += 1

            if include_paper_selectors:
                with tabs[tab_idx]:
                    selections["paper_numbers"], selections["paper_variants"] = _render_paper_tab(
                        selected_subject, selections["topics"], selections["subtopics"],
                        selections["years"], selections["variants"]
                    )
                tab_idx += 1

            with tabs[tab_idx]:
                ready = selections["paper_variants"] if include_paper_selectors else selections["years"]
                selections["difficulties"] = _render_difficulty_tab(
                    selected_subject, selections["topics"], selections["subtopics"],
                    selections["years"], selections["variants"], selections["paper_numbers"],
                    selections["paper_variants"], bool(ready)
                )

        # Quick-glance chip summary so the collapsed popover doesn't hide state
        chips = []
        for label, values in [("Topics", selections["topics"]), ("Years", selections["years"]),
                               ("Variants", selections["variants"]), ("Difficulty", selections["difficulties"])]:
            if values:
                chips.append(f"`{label}: {len(values)}`")
        if chips:
            st.caption(" ".join(chips))

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
        <div class="pf-card" style="text-align:center; padding: 3rem 1rem;">
            <div style="font-size: 2.5rem;">{icon}</div>
            <div style="font-size: 1.15rem; font-weight: 700; margin-top: .5rem;">{title}</div>
            <div style="color: var(--text-muted); margin-top: .25rem;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Paper detail card
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
        ("Subject Code", details["subject_code"]), ("Year", details["year"]),
        ("Variant", details["variant"]), ("Paper Variant", details["paper_variant"]),
        ("Question No.", details["question_number"]),
    ]
    for col, (label, value) in zip(cols, labels):
        col.metric(label, value)

    mapping = utils.get_mapping(details["variant"])
    snippet = utils.generate_snippet(details["subject_code"], details["paper_variant"], mapping, details["year"])
    st.code(snippet, language="text")


# ---------------------------------------------------------------------------
# Gamification widgets
# ---------------------------------------------------------------------------
def render_badge_shelf(badges: list[dict]) -> None:
    earned = [b for b in badges if b["earned"]]
    st.caption(f"{len(earned)}/{len(badges)} badges earned")
    html = ['<div class="pf-badge-shelf">']
    for b in badges:
        cls = "pf-badge earned" if b["earned"] else "pf-badge"
        icon = "🏅" if b["earned"] else "🔒"
        html.append(f'<div class="{cls}" title="{b["description"]}">{icon} {b["name"]}</div>')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_streak_indicator(streak: dict) -> None:
    flame_class = "pf-streak-flame active" if streak["current"] > 0 else "pf-streak-flame"
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:.6rem;">
            <span class="{flame_class}">🔥</span>
            <div>
                <div style="font-weight:800; font-size:1.3rem; line-height:1;">{streak['current']} day{'s' if streak['current'] != 1 else ''}</div>
                <div style="color:var(--text-muted); font-size:.8rem;">current streak · best {streak['longest']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Worksheet "cart"
# ---------------------------------------------------------------------------
def add_paper_to_cart(question_path: str, answer_path: str, label: str) -> bool:
    """Returns False if the item was already in the cart (no-op), True if added."""
    cart = st.session_state.setdefault("worksheet_cart", [])
    if any(item["question_path"] == question_path for item in cart):
        return False
    cart.append({"question_path": question_path, "answer_path": answer_path, "label": label})
    return True


def render_cart_summary() -> list[dict]:
    cart = st.session_state.get("worksheet_cart", [])
    if not cart:
        render_empty_state("Your worksheet cart is empty", "Browse filtered results and add questions to build a custom set.", icon="🛒")
        return cart

    st.caption(f"{len(cart)} question(s) in your cart")
    for i, item in enumerate(cart):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f'<div class="pf-cart-item">{item["label"]}</div>', unsafe_allow_html=True)
        if c2.button("✕", key=f"remove_cart_{i}", help="Remove"):
            cart.pop(i)
            st.rerun()
    return cart