"""
profile.py

Pastify has no login system. To let streaks/badges/history mean anything
across a session, we ask for a simple display name once (via st.dialog) and
key all progress rows in progress.db by it. This is explicitly NOT
authentication — it's a convenience label. See progress.py's docstring for
the multi-tenant caveat.
"""

import streamlit as st


def get_profile() -> str:
    """Dialog-capable entry point. Call this EXACTLY ONCE per script run —
    from Home.py, before st.navigation routes to a page — never from
    inside a page's own render(). st.dialog-decorated functions can't be
    safely invoked twice in the same run (duplicate widget keys), so every
    page below reads the already-resolved name via current_profile()
    instead of calling this again."""
    if "student_name" in st.session_state and st.session_state.student_name:
        return st.session_state.student_name

    _prompt_for_profile()
    return st.session_state.get("student_name", "Guest")


def current_profile() -> str:
    """Cheap, dialog-free read for use inside individual pages. Safe to
    call as many times as you like in the same run."""
    return st.session_state.get("student_name", "Guest")


@st.dialog("Welcome to Pastify 👋")
def _prompt_for_profile():
    st.write("What should we call you? This just labels your streaks and progress on this device — no account needed.")
    name = st.text_input("Display name", placeholder="e.g. Alex", key="profile_name_input")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continue", type="primary", use_container_width=True, disabled=not name.strip()):
            st.session_state.student_name = name.strip()
            st.rerun()
    with col2:
        if st.button("Continue as Guest", use_container_width=True):
            st.session_state.student_name = "Guest"
            st.rerun()


def render_profile_badge() -> None:
    """Small sidebar element showing who's logged in + a way to switch profile."""
    name = st.session_state.get("student_name", "Guest")
    with st.sidebar:
        cols = st.columns([3, 1])
        cols[0].caption(f"👤 **{name}**")
        if cols[1].button("↺", help="Switch profile", key="switch_profile_btn"):
            st.session_state.pop("student_name", None)
            st.rerun()
