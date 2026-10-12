
"""
Pastify theme system.

Two per-session visual themes:
- Warm Ivory (light)
- Midnight Neon (dark)

Never modifies Streamlit's global config at runtime.
"""

import streamlit as st

from config import CSS_PATH


LIGHT_VARS = {
    "--pf-primary-color": "#527DA0",
    "--pf-accent-color": "#7095B2",
    "--pf-success-color": "#288565",
    "--pf-warning-color": "#B47B25",
    "--pf-danger-color": "#C75058",
    "--pf-background-color": "#FAF8F4",
    "--pf-secondary-background-color": "#F0EAE0",
    "--pf-surface-color": "#FFFFFF",
    "--pf-text-color": "#303741",
    "--pf-text-muted": "#69737D",
    "--pf-border-color": "rgba(48, 55, 65, 0.12)",
    "--pf-shadow-color": "rgba(48, 55, 65, 0.09)",
    "--pf-on-primary-color": "#FFFFFF",
    "--pf-glow-color": "rgba(82, 125, 160, 0.12)",
}

DARK_VARS = {
    "--pf-primary-color": "#31DFFF",
    "--pf-accent-color": "#6794FF",
    "--pf-success-color": "#5DF2A0",
    "--pf-warning-color": "#F5DD55",
    "--pf-danger-color": "#FF526B",
    "--pf-background-color": "#080F20",
    "--pf-secondary-background-color": "#101A30",
    "--pf-surface-color": "#14213B",
    "--pf-text-color": "#EAF2FF",
    "--pf-text-muted": "#A3B4D0",
    "--pf-border-color": "rgba(113, 153, 207, 0.22)",
    "--pf-shadow-color": "rgba(0, 0, 0, 0.35)",
    "--pf-on-primary-color": "#080F20",
    "--pf-glow-color": "rgba(49, 223, 255, 0.18)",
}


def get_theme_vars() -> dict[str, str]:
    """Return the palette selected for the current session."""
    return DARK_VARS if st.context.theme.get("type") == "dark" else LIGHT_VARS


def get_theme_color(name: str) -> str:
    """Retrieve a theme color for Python-rendered elements, including charts."""
    return get_theme_vars()[name]


def _vars_to_css(vars_dict: dict[str, str]) -> str:
    """Expose the active palette to the app and portaled widgets."""
    declarations = "\n".join(
        f"    {name}: {value} !important;"
        for name, value in vars_dict.items()
    )

    return (
        "<style>\n"
        ":root, html, body, .stApp {\n"
        f"{declarations}\n"
        "}\n"
        "</style>"
    )


def inject_theme() -> None:
    """Apply the current session's CSS palette."""
    st.markdown(
        _vars_to_css(get_theme_vars()),
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _read_css() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def load_css() -> None:
    """Load the shared stylesheet."""
    st.markdown(
        f"<style>{_read_css()}</style>",
        unsafe_allow_html=True,
    )


def apply_page_theme() -> None:
    """Apply both the active palette and shared stylesheet."""
    inject_theme()
    load_css()



def theme_toggle() -> None:
    """Theme selection is handled by Streamlit's built-in menu."""
    pass


@st.fragment(run_every="1s")
def sync_native_theme() -> None:
    """Refresh Pastify when Streamlit's native theme changes."""
    current = st.context.theme.get("type", "light")
    previous = st.session_state.get("_pf_native_theme")

    if previous is None:
        st.session_state["_pf_native_theme"] = current
    elif previous != current:
        st.session_state["_pf_native_theme"] = current
        st.rerun()
