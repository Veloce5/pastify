"""my_progress.py — the advanced analytics dashboard (new page)."""

import streamlit as st

import theme
import progress
from profile import current_profile, render_profile_badge
from components import render_badge_shelf, render_streak_indicator, render_empty_state
from analytics import render_accuracy_heatmap, render_time_per_question, render_progress_trend, render_accuracy_donut
from database import get_subjects


def render():
    theme.apply_page_theme()
    profile = current_profile()
    with st.sidebar:
        theme.theme_toggle()
    render_profile_badge()

    st.title("📈 My Progress")
    st.write(f"A full breakdown of {profile}'s practice history across Pastify.")

    history = progress.get_history(profile)
    if not history:
        render_empty_state(
            "No activity yet",
            "Complete a Quiz or Timed Test and your stats will show up here.",
            icon="📈",
        )
        return

    total = len(history)
    correct = sum(h["is_correct"] for h in history)
    streak = progress.compute_streak(profile)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Questions answered", total)
    m2.metric("Accuracy", f"{correct / total * 100:.0f}%")
    m3.metric("Current streak", f"{streak['current']}d")
    m4.metric("Best streak", f"{streak['longest']}d")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Accuracy by Topic", "Pacing", "Activity Trend", "Badges"])

    with tab1:
        subjects = sorted({h["subject"] for h in history if h["subject"]})
        subject_filter = st.selectbox("Filter by subject", ["All subjects"] + subjects, key="progress_subject_filter")
        subj = None if subject_filter == "All subjects" else subject_filter
        topic_accuracy = progress.get_topic_accuracy(profile, subject=subj)
        render_accuracy_heatmap(topic_accuracy)

        wrong = total - correct
        c1, c2 = st.columns([1, 2])
        with c1:
            render_accuracy_donut(correct, wrong)
        with c2:
            st.caption("Weakest topics (lowest accuracy, min. 3 attempts)")
            weak = sorted(
                [(t, s) for t, s in topic_accuracy.items() if s["total"] >= 3],
                key=lambda kv: kv[1]["accuracy"],
            )[:5]
            if weak:
                for topic_name, stats in weak:
                    st.write(f"- **{topic_name}** — {stats['accuracy']*100:.0f}% ({stats['correct']}/{stats['total']})")
            else:
                st.caption("Not enough attempts per topic yet to highlight weak spots.")

    with tab2:
        st.caption("Time taken per question (timed attempts only) — green = correct, red = incorrect")
        render_time_per_question(history)

    with tab3:
        st.caption("Questions answered per day, last 30 days")
        render_progress_trend(progress.get_daily_activity(profile, days=30))

    with tab4:
        render_badge_shelf(progress.compute_badges(profile))


render()
