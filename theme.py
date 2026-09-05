"""
theme.py  (replaces theme_management.py)

The original implementation wrote `~/.streamlit/config.toml` on every
toggle. On any deployment with more than one concurrent user, that's a
shared, server-wide file — one person flipping to dark mode changes the
theme for *everyone else's* browser tab too, and it typically requires a
full app restart to reliably take effect.

This version keeps the toggle 100% client-side and per-session: it injects
a small <style> block that overrides Streamlit's own CSS custom properties
for this render only. No filesystem writes, no cross-user leakage, and it
applies instantly on the same rerun the toggle was clicked in.
"""

import streamlit as st

from config import CSS_PATH

LIGHT_VARS = {
    "--primary-color": "#2563EB",
    "--background-color": "#FFFFFF",
    "--secondary-background-color": "#F8FAFC",
    "--text-color": "#0F172A",
    "--border-color": "rgba(15, 23, 42, 0.10)",
}

DARK_VARS = {
    "--primary-color": "#3B82F6",
    "--background-color": "#0F172A",
    "--secondary-background-color": "#1E293B",
    "--text-color": "#F8FAFC",
    "--border-color": "rgba(248, 250, 252, 0.12)",
}


def _vars_to_css(vars_dict: dict) -> str:
    body = "\n".join(f"    {k}: {v} !important;" for k, v in vars_dict.items())
    return (
        "<style>\n"
        f":root, .stApp {{\n{body}\n}}\n"
        "</style>"
    )


def inject_theme() -> None:
    """Apply the current session's theme override. Call once near the top
    of every page, after set_page_config()."""
    is_dark = st.session_state.get("dark_mode", False)
    st.markdown(_vars_to_css(DARK_VARS if is_dark else LIGHT_VARS), unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _read_css() -> str:
    return CSS_PATH.read_text()


def load_css() -> None:
    st.markdown(f"<style>{_read_css()}</style>", unsafe_allow_html=True)


def apply_page_theme() -> None:
    """One call, at the top of every page: applies the light/dark variable
    override for this session, then loads the static stylesheet."""
    inject_theme()
    load_css()


def theme_toggle() -> None:
    """Render the Dark Mode toggle. Safe to call from any page's sidebar."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    new_value = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_mode_toggle")
    if new_value != st.session_state.dark_mode:
        st.session_state.dark_mode = new_value
        st.rerun()
