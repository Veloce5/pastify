"""
Pastify — What's New

User-facing release notes, ordered from newest to oldest.
Add future releases to the RELEASES list.
"""

import streamlit as st

RELEASES = [
    {
        "version": "1.2.0",
        "title": "Infrastructure & Platform Improvements",
        "date": "October 2026",
        "latest": True,
        "sections": {
            "New": [
                "Added 1,340 multiple-choice questions, expanding the question bank to 12,383 questions.",
            ],
            "Improved": [
                "Improved PDF processing and question-bank infrastructure.",
                "Introduced access-controlled private PDF storage.",
                "Improved platform reliability and application navigation.",
                "Continued improvements to question browsing, worksheets, quizzes, timed tests, and progress tracking.",
            ],
            "Important Notice": [
                "Cambridge examination PDFs, mark schemes, and generated PDF downloads are currently unavailable due to copyright restrictions. Other Pastify features remain accessible.",
            ],
        },
    },
    {
        "version": "1.1.0",
        "title": "MCQ Expansion",
        "date": "October 2026",
        "latest": False,
        "sections": {
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
        if release["version"] == "1.1.0":
            # PASTIFY_OCTOBER_2026_UPDATE
            st.subheader("October 2026 — Platform Update")
            st.markdown("""
            Pastify continues to offer its core study tools:

            - **Browse Papers:** Explore questions using subject and paper filters.
            - **Worksheet Builder:** Select questions and organize custom worksheets.
            - **Quiz Mode:** Practice using interactive quiz controls.
            - **Timed Test:** Practice with a timed session.
            - **My Progress:** Review your practice activity.
            - **Platform improvements:** Updates to PDF storage infrastructure, navigation, and reliability.

            **Important copyright update:** Cambridge examination PDFs, including question papers, mark schemes, and generated PDF downloads, are temporarily unavailable due to copyright restrictions. Other Pastify features remain accessible.
            """)
            st.divider()
