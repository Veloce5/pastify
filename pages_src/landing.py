"""landing.py — premium hero + launcher tiles + at-a-glance progress."""

import streamlit as st

import theme
import progress
from profile import current_profile, render_profile_badge
from components import render_badge_shelf, render_streak_indicator

FOOTER_LINKS = [
    {"label": "Privacy Policy", "url": "#"},
    {"label": "Terms of Service", "url": "#"},
]


def _render_footer():
    links_html = " | ".join(f'<a href="{link["url"]}">{link["label"]}</a>' for link in FOOTER_LINKS)
    st.markdown(f'<div class="footer"><p>&copy; 2026 Pastify | {links_html}</p></div>', unsafe_allow_html=True)


def render():
    theme.apply_page_theme()
    profile = current_profile()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.markdown(
        f"""
        <div class="pf-hero">
            <div style="font-size:.95rem; font-weight:600; opacity:.85;">Welcome back, {profile} 👋</div>
            <h1 style="margin-top:.3rem;">Master Cambridge A-Levels,<br>one past paper at a time.</h1>
            <p class="pf-subtle" style="font-size:1.05rem; max-width:560px;">
                Filter by topic and difficulty, drill with instant-feedback quizzes,
                simulate exam conditions, and watch your progress compound.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    streak = progress.compute_streak(profile)
    badges = progress.compute_badges(profile)

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container(border=True):
            render_streak_indicator(streak)
    with col2:
        with st.container(border=True):
            st.caption("Your badges")
            render_badge_shelf(badges)

    st.write("")
    st.subheader("Where to next?")

    tiles = [
        ("📚", "Browse Papers", "Filter and read past papers question-by-question.", "pages_src/browse.py"),
        ("📝", "Worksheet Builder", "Build a custom set and export a merged PDF.", "pages_src/worksheet.py"),
        ("🎮", "Quiz Mode", "Untimed practice with instant feedback.", "pages_src/quiz.py"),
        ("⏱️", "Timed Test", "Simulate real exam conditions.", "pages_src/timed_test.py"),
    ]
    cols = st.columns(4)
    for col, (icon, title, desc, target) in zip(cols, tiles):
        with col:
            st.markdown(
                f"""
                <div class="pf-tile">
                    <div class="pf-tile-icon">{icon}</div>
                    <div class="pf-tile-title">{title}</div>
                    <div class="pf-tile-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Open →", key=f"nav_{title}", width="stretch"):
                st.switch_page(target)

    st.write("")
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("📈 View My Progress", width="stretch"):
            st.switch_page("pages_src/my_progress.py")
        if st.button("👥 About Us", width="stretch"):
            st.switch_page("pages_src/about.py")

    _render_footer()


render()
