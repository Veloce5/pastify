"""
Home.py

Entry point. Uses Streamlit's native multipage router (st.navigation +
st.Page) instead of hand-rolled session_state routing. The profile prompt
(profile.get_profile) runs here, before any page, so every page can assume
a profile name already exists in session_state.
"""

import streamlit as st

from profile import get_profile

st.set_page_config(
    page_title="Pastify — Past Paper Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

from theme import sync_native_theme
sync_native_theme()



get_profile()  # shows the welcome dialog once per session if needed

pages = [
    st.Page("pages_src/landing.py", title="Home", icon="🏠", default=True),
    st.Page("pages_src/browse.py", title="Browse Papers", icon="📚"),
    st.Page("pages_src/worksheet.py", title="Worksheet Builder", icon="📝"),
    st.Page("pages_src/quiz.py", title="Quiz Mode", icon="🎮"),
    st.Page("pages_src/timed_test.py", title="Timed Test", icon="⏱️"),
    st.Page("pages_src/my_progress.py", title="My Progress", icon="📈"),
    st.Page("pages_src/about.py", title="About Us", icon="👥"),
]

pg = st.navigation(pages)
pg.run()
