"""About Pastify and the people building it."""

import streamlit as st

import theme
from profile import render_profile_badge


FOUNDERS = (
    {
        "name": "Veer Sanghvi",
        "role": "Co-Founder & Frontend Lead",
        "bio": (
            "A former Cambridge student focused on making Pastify clear, "
            "approachable, and easy to use. Veer leads the frontend "
            "experience and user-facing design."
        ),
        "github": "https://github.com/9958ViceVortex",
        "linkedin": "https://www.linkedin.com/in/veer-sanghvi-b34214379/",
    },
    {
        "name": "Dev Joshi",
        "role": "Co-Founder & Backend Lead",
        "bio": (
            "A former Cambridge student and Computer Science undergraduate "
            "at Stony Brook University. Dev focuses on Pastify's "
            "application logic, database, and PDF-processing systems."
        ),
        "github": "https://github.com/Veloce5",
        "linkedin": "https://www.linkedin.com/in/dev-joshi-1310ab346/",
    },
)


def _founder_card(founder: dict[str, str]) -> None:
    with st.container(border=True):
        st.subheader(founder["name"])
        st.caption(founder["role"])
        st.write(founder["bio"])
        linkedin_col, github_col = st.columns(2)
        with linkedin_col:
            st.link_button("LinkedIn ↗", founder["linkedin"], use_container_width=True)
        with github_col:
            st.link_button("GitHub ↗", founder["github"], use_container_width=True)


def render() -> None:
    theme.apply_page_theme()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("About Pastify")
    st.write(
        "Pastify is a free, student-built platform designed to make "
        "past-paper revision more focused and practical."
    )

    st.subheader("Our Story")
    st.write(
        "As former Cambridge students, we know how much time can go into "
        "searching through papers for the right question. We started Pastify "
        "to make it easier to discover questions, build targeted practice, "
        "and understand progress in one place."
    )

    st.subheader("Meet the Founders")
    left, right = st.columns(2, gap="medium")
    for column, founder in zip((left, right), FOUNDERS):
        with column:
            _founder_card(founder)

    st.divider()
    st.subheader("Our Mission")
    st.write(
        "Make exam preparation more accessible through thoughtful tools "
        "for question discovery, practice, and progress tracking — "
        "without charging students to use Pastify."
    )

    st.caption(
        "Pastify is an independent student project and is not affiliated "
        "with or endorsed by Cambridge International. Copyright permission "
        "for displaying Cambridge examination materials has been requested "
        "and has not yet been granted."
    )


render()
