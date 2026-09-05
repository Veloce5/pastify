"""landing.py — the marketing/launcher landing page shown at the app root."""

import streamlit as st

import theme

FOOTER_LINKS = [
    {"label": "Privacy Policy", "url": "#"},
    {"label": "Terms of Service", "url": "#"},
]


def _render_footer():
    links_html = " | ".join(f'<a href="{l["url"]}">{l["label"]}</a>' for l in FOOTER_LINKS)
    st.markdown(
        f"""
        <div class="footer">
            <p>&copy; 2026 Pastify | {links_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()

    st.markdown("<div class='hero-spacer'></div>", unsafe_allow_html=True)
    st.title("Welcome to Pastify")
    st.subheader("Filter, practice, and master past papers by topic, year, and difficulty.")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button("📚 Past Paper Filtering Tool", use_container_width=True, key="nav_browse"):
            st.switch_page("pages_src/browse.py")
        if st.button("📝 Worksheet Builder", use_container_width=True, key="nav_worksheet"):
            st.switch_page("pages_src/worksheet.py")
    with col2:
        if st.button("🎮 Quiz Mode", use_container_width=True, key="nav_quiz"):
            st.switch_page("pages_src/quiz.py")
        if st.button("⏱️ Timed Test", use_container_width=True, key="nav_timed"):
            st.switch_page("pages_src/timed_test.py")

    st.markdown("<br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("👥 About Us", use_container_width=True, key="nav_about"):
            st.switch_page("pages_src/about.py")

    _render_footer()


render()
