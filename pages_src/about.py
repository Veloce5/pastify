"""about.py (replaces aboutus.py)"""

import streamlit as st

import theme
from config import LOGO_PATH


def render():
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()

    st.title("About Us")
    st.write("Meet the minds behind Pastify.")

    col1, col2 = st.columns(2)
    team = [
        ("Veer Sanghvi", "Co-Founder & Frontend Lead"),
        ("Dev Joshi", "Co-Founder & Backend Lead"),
    ]

    for col, (name, role) in zip((col1, col2), team):
        with col:
            st.header(name)
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), width=300)
            st.subheader(f"Role: {role}")
            st.write(
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
                "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
                "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
            )

    st.markdown("---")
    st.subheader("Our Mission")
    st.write(
        "We strive to deliver impactful, insightful, and innovative content to our users, "
        "empowering them to make informed decisions."
    )


render()
