"""
analytics.py

Chart builders for the "My Progress" dashboard. Kept separate from
progress.py (data access) and components.py (generic UI) since these are
specifically plotly figure factories — swap the charting library here
without touching how history is stored or queried.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Centralized design system for Plotly (matching the CSS theme)
CHART_THEME = {
    "primary": "#4F46E5",
    "primary_transparent": "rgba(79,70,229,0.15)",
    "success": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "bg_transparent": "rgba(0,0,0,0)"
}


def render_accuracy_heatmap(topic_accuracy: dict[str, dict]) -> None:
    """Topic-by-accuracy heatmap. Renders an empty state instead of an
    empty/broken chart when there's no data yet."""
    if not topic_accuracy:
        st.info("📊 No attempts logged yet — answer a few questions to see your accuracy by topic.")
        return

    topics = list(topic_accuracy.keys())
    accuracies = [topic_accuracy[t]["accuracy"] * 100 for t in topics]
    totals = [topic_accuracy[t]["total"] for t in topics]

    fig = go.Figure(data=go.Heatmap(
        z=[accuracies],
        x=topics,
        y=["Accuracy"],
        colorscale=[
            [0, CHART_THEME["danger"]], 
            [0.5, CHART_THEME["warning"]], 
            [1, CHART_THEME["success"]]
        ],
        zmin=0, zmax=100,
        text=[[f"{a:.0f}%<br>({n} qs)" for a, n in zip(accuracies, totals)]],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="Accuracy %"),
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=10, b=80),
        xaxis=dict(tickangle=-35),
        paper_bgcolor=CHART_THEME["bg_transparent"],
        plot_bgcolor=CHART_THEME["bg_transparent"],
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_time_per_question(history: list[dict]) -> None:
    """Time taken per question over the session/history, to spot pacing issues."""
    timed = [h for h in history if h.get("time_taken_seconds") is not None]
    if not timed:
        st.info("⏱️ No timed attempts logged yet.")
        return

    x = list(range(1, len(timed) + 1))
    y = [h["time_taken_seconds"] for h in timed]
    colors = [CHART_THEME["success"] if h["is_correct"] else CHART_THEME["danger"] for h in timed]

    fig = go.Figure(data=go.Bar(x=x, y=y, marker_color=colors))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Question #",
        yaxis_title="Seconds taken",
        paper_bgcolor=CHART_THEME["bg_transparent"],
        plot_bgcolor=CHART_THEME["bg_transparent"],
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_progress_trend(daily_activity: dict[str, int]) -> None:
    """Attempts-per-day over the recent window — the classic streak graph."""
    if not daily_activity or not any(daily_activity.values()):
        st.info("📈 No activity in this window yet.")
        return

    dates = list(daily_activity.keys())
    counts = list(daily_activity.values())

    fig = px.area(x=dates, y=counts, labels={"x": "Date", "y": "Questions answered"})
    fig.update_traces(
        line_color=CHART_THEME["primary"], 
        fillcolor=CHART_THEME["primary_transparent"]
    )
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=CHART_THEME["bg_transparent"],
        plot_bgcolor=CHART_THEME["bg_transparent"],
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_accuracy_donut(correct: int, wrong: int) -> None:
    total = correct + wrong
    if total == 0:
        st.info("No attempts yet.")
        return
        
    fig = go.Figure(data=[go.Pie(
        labels=["Correct", "Incorrect"],
        values=[correct, wrong],
        hole=0.65,
        marker_colors=[CHART_THEME["success"], CHART_THEME["danger"]],
        textinfo="percent",
    )])
    fig.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        paper_bgcolor=CHART_THEME["bg_transparent"],
        annotations=[dict(text=f"{total}", x=0.5, y=0.5, font_size=22, showarrow=False)],
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})