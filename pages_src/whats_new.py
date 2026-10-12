"""
Pastify — What's New

User-facing release notes, ordered from newest to oldest.
Add future releases to the RELEASES list.
"""

import streamlit as st

RELEASES = [
    {
        "version": "1.1.0",
        "title": "MCQ Expansion",
        "date": "October 2026",
        "latest": True,
        "sections": {
            "New": [
                "Added 1,340 multiple-choice questions across the question bank.",
                "Expanded the question bank to 12,383 questions.",
            ],
            "Improved": [
                "Improved MCQ PDF processing and question availability.",
                "Questions without recorded answers are excluded from quizzes.",
            ],
        },
    },
    {
        "version": "1.0.0",
        "title": "Initial Release",
        "date": "Initial launch",
        "latest": False,
        "sections": {
            "Launched": [
                "Browse Cambridge A-Level past-paper questions.",
                "Build worksheets from selected questions.",
                "Practise with Quiz Mode and Timed Test.",
                "Track learning progress.",
            ],
        },
    },
]


def render_release(release):
    version = release["version"]
    title = release["title"]

    st.markdown(f"### v{version} — {title}")

    if release["latest"]:
        st.caption(f"🟢 Latest release · {release['date']}")
    else:
        st.caption(release["date"])

    for section, items in release["sections"].items():
        st.markdown(f"**{section}**")
        for item in items:
            st.markdown(f"- {item}")


st.title("✨ What's New")
st.write(
    "Explore the latest improvements, new features, "
    "and updates to Pastify."
)

st.divider()

render_release(RELEASES[0])

st.divider()

with st.expander("Previous releases", expanded=False):
    for release in RELEASES[1:]:
        render_release(release)
