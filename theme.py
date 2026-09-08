"""
theme.py

Per-session CSS-variable theme override (never writes a global config.toml
— see MIGRATION_NOTES.md for why that was a real multi-user bug in an
earlier version). This version adds a richer premium palette: a proper
accent/success/warning/danger scale instead of just one primary color, so
badges, accuracy states, and charts all pull from the same system instead
of ad-hoc hex codes scattered through the codebase.
"""

import streamlit as st

from config import CSS_PATH

LIGHT_VARS = {
    "--primary-color": "#4F46E5",       # indigo — primary actions
    "--accent-color": "#7C3AED",        # violet — secondary accents / gradients
    "--success-color": "#059669",
    "--warning-color": "#D97706",
    "--danger-color": "#DC2626",
    "--background-color": "#FFFFFF",
    "--secondary-background-color": "#F8FAFC",
    "--surface-color": "#FFFFFF",
    "--text-color": "#0F172A",
    "--text-muted": "#64748B",
    "--border-color": "rgba(15, 23, 42, 0.08)",
    "--shadow-color": "rgba(15, 23, 42, 0.06)",
}

DARK_VARS = {
    "--primary-color": "#818CF8",
    "--accent-color": "#A78BFA",
    "--success-color": "#34D399",
    "--warning-color": "#FBBF24",
    "--danger-color": "#F87171",
    "--background-color": "#0B1120",
    "--secondary-background-color": "#151E30",
    "--surface-color": "#1B2537",
    "--text-color": "#F1F5F9",
    "--text-muted": "#94A3B8",
    "--border-color": "rgba(241, 245, 249, 0.10)",
    "--shadow-color": "rgba(0, 0, 0, 0.35)",
}


def _vars_to_css(vars_dict: dict) -> str:
    body = "\n".join(f"    {k}: {v} !important;" for k, v in vars_dict.items())
    return f"<style>\n:root, .stApp {{\n{body}\n}}\n</style>"


def inject_theme() -> None:
    is_dark = st.session_state.get("dark_mode", False)
    st.markdown(_vars_to_css(DARK_VARS if is_dark else LIGHT_VARS), unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _read_css() -> str:
    return CSS_PATH.read_text()


def load_css() -> None:
    st.markdown(f"<style>{_read_css()}</style>", unsafe_allow_html=True)


def apply_page_theme() -> None:
    inject_theme()
    load_css()


def theme_toggle() -> None:
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    new_value = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_mode_toggle")
    if new_value != st.session_state.dark_mode:
        st.session_state.dark_mode = new_value
        st.rerun()
