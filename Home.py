"""
Home.py (replaces home.py)

The original app hand-rolled page routing with a `session_state["current_page"]`
string and a big if/elif chain, plus a manually duplicated "Back to Home"
sidebar block on every branch. This uses Streamlit's native multipage
router (`st.navigation` + `st.Page`), which gives proper URLs per page,
a built-in nav sidebar, and removes ~40 lines of bespoke routing logic.
"""

import streamlit as st

st.set_page_config(
    page_title="Pastify — Past Paper Filter Tool",
    page_icon="📚",
    layout="centered",
)

pages = [
    st.Page("pages_src/landing.py", title="Home", icon="🏠", default=True),
    st.Page("pages_src/browse.py", title="Browse Papers", icon="📚"),
    st.Page("pages_src/worksheet.py", title="Worksheet Builder", icon="📝"),
    st.Page("pages_src/quiz.py", title="Quiz Mode", icon="🎮"),
    st.Page("pages_src/timed_test.py", title="Timed Test", icon="⏱️"),
    st.Page("pages_src/about.py", title="About Us", icon="👥"),
]

pg = st.navigation(pages)  # default "sidebar" position: a clean nav menu above every page's filters
pg.run()
