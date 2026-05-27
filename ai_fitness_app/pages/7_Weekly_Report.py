import streamlit as st # pyright: ignore[reportMissingImports]
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # type: ignore
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from groq import Groq # pyright: ignore[reportMissingImports]
import os
from utils.sidebar import show_sidebar
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from utils.db import (
    get_weekly_summary, get_habit_history, get_diet_history,
    get_body_stats_history, get_sleep_history, get_workout_history,
    get_full_context_for_ai, get_personal_records
)
from datetime import date
show_sidebar()
load_dotenv()

st.set_page_config(page_title="AI Weekly Report", page_icon="📑", layout="wide")
st.title("📑 AI Weekly Performance Report")
st.markdown("Your personal AI coach analyzes your week and gives **data-driven recommendations**")

GROQ_MODEL = "llama-3.1-8b-instant"

# ── Pull data ──────────────────────────────────────────────────────────────────
summary = get_weekly_summary()
habit_df = get_habit_history(7)
sleep_df = get_sleep_history(7)
workout_df = get_workout_history(20)
body_df = get_body_stats_history()
prs = get_personal_records()

# ── KPI Overview ───────────────────────────────────────────────────────────────
st.subheader("📊 This Week at a Glance")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Workouts", summary["workouts"], help="Sessions this week")
k2.metric("Cal Burned", f"{summary['calories_burned']} kcal")
k3.metric("Streak", f"{summary['streak']} days")
k4.metric("Avg Mood", f"{summary['avg_mood']}/10")
k5.metric("Avg Sleep", f"{summary['avg_sleep']}h",
          "✅" if summary['avg_sleep'] >= 7 else "⚠️")

# Recovery score
mood = summary.get("avg_mood", 5)
sleep = min(summary.get("avg_sleep", 6), 9)
streak = min(summary.get("streak", 0), 7)
recovery = int((mood / 10 * 40) + (sleep / 9 * 40) + (streak / 7 * 20))
k6.metric("Recovery", f"{recovery}/100",
          "💪 Great" if recovery >= 70 else "⚠️ Low")

st.divider()

# ── Charts row ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("🏋️ Workout Frequency")
    if not workout_df.empty:
        workout_df["date"] = pd.to_datetime(workout_df["date"])
        daily_w = workout_df.groupby("date").size().reset_index(name="sessions")
        fig_wf = px.bar(daily_w, x="date", y="sessions",
                        color_discrete_sequence=["#1D9E75"], height=220)
        fig_wf.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)",
                             margin=dict(t=10, b=10))
        st.plotly_chart(fig_wf, use_container_width=True)
    else:
        st.info("No workouts yet")

with c2:
    st.subheader("😴 Sleep vs Mood")
    if not habit_df.empty and not sleep_df.empty:
        # Merge on date
        habit_df["date"] = pd.to_datetime(habit_df["date"])
        sleep_df["date"] = pd.to_datetime(sleep_df["date"])
        merged = pd.merge(habit_df[["date", "mood"]], sleep_df[["date", "hours"]],
                          on="date", how="inner")
        if not merged.empty:
            fig_sm = px.scatter(merged, x="hours", y="mood",
                                size_max=12, color_discrete_sequence=["#9B59B6"],
                                labels={"hours": "Sleep Hours", "mood": "Mood"},
                                height=220)
            fig_sm.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                 paper_bgcolor="rgba(0,0,0,0)",
                                 margin=dict(t=10, b=10))
            st.plotly_chart(fig_sm, use_container_width=True)
    else:
        st.info("Log sleep + habits to see correlation")

with c3:
    st.subheader("🏆 Personal Records")
    if not prs.empty:
        fig_pr = px.bar(prs, x="exercise", y="best_weight",
                        color_discrete_sequence=["#EF9F27"],
                        labels={"best_weight": "Weight (kg)", "exercise": "Exercise"},
                        height=220)
        fig_pr.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)",
                             margin=dict(t=10, b=10))
        st.plotly_chart(fig_pr, use_container_width=True)
    else:
        st.info("No PRs yet")

st.divider()

# ── Weight progress ────────────────────────────────────────────────────────────
if not body_df.empty and "weight_kg" in body_df.columns:
    st.subheader("⚖️ Weight Progress")
    body_df["date"] = pd.to_datetime(body_df["date"])
    body_df = body_df.sort_values("date")
    body_df["7d_avg"] = body_df["weight_kg"].rolling(7, min_periods=1).mean()

    fig_wt = go.Figure()
    fig_wt.add_trace(go.Scatter(
        x=body_df["date"], y=body_df["weight_kg"],
        mode="markers", name="Daily", marker=dict(color="#378ADD", size=6)
    ))
    fig_wt.add_trace(go.Scatter(
        x=body_df["date"], y=body_df["7d_avg"],
        mode="lines", name="7-Day Avg",
        line=dict(color="#1D9E75", width=2.5)
    ))
    fig_wt.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=230, margin=dict(t=10, b=10),
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_wt, use_container_width=True)
    st.divider()

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.subheader("🤖 AI Performance Analysis")
st.markdown("Get your personalized weekly coaching report from FitBot")

goal = st.selectbox("Your primary goal", [
    "Lose weight", "Gain muscle", "Improve fitness", "Maintain health", "Athletic performance"
])

col_btn, col_info = st.columns([1, 3])
with col_btn:
    generate = st.button("📑 Generate My Report", type="primary", use_container_width=True)
with col_info:
    st.caption("This uses your actual workout, diet, sleep, and body data from this week")

if generate:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in .env")
    else:
        user_context = get_full_context_for_ai()

        # Build exercise breakdown for prompt
        ex_breakdown = ""
        if not workout_df.empty:
            ex_counts = workout_df.groupby("exercise").agg(
                sessions=("reps", "count"),
                total_reps=("reps", "sum"),
                avg_form=("form_score", "mean")
            ).reset_index()
            ex_breakdown = ex_counts.to_string(index=False)

        # Diet summary
        diet_df = get_diet_history(7)
        diet_summary = ""
        if not diet_df.empty:
            daily_cals = diet_df.groupby("date")["calories"].sum()
            diet_summary = (
                f"Avg daily calories: {daily_cals.mean():.0f} kcal, "
                f"Range: {daily_cals.min():.0f}–{daily_cals.max():.0f}"
            )

        with st.spinner("FitBot is analyzing your week... 📊"):
            try:
                client = Groq(api_key=api_key)
                prompt = f"""You are a world-class personal trainer and sports nutritionist.
Generate a comprehensive weekly fitness performance report for this user.

{user_context}

Exercise breakdown this week:
{ex_breakdown if ex_breakdown else 'No workouts logged'}

Diet summary this week:
{diet_summary if diet_summary else 'No diet logged'}

Primary goal: {goal}

Write a professional weekly report with these sections:

## 💪 Workout Performance
Analyze frequency, consistency, exercises done, form scores if available. Rate their effort.

## 🥗 Nutrition Assessment
Assess calorie intake vs likely goal, macro balance, water intake. Identify gaps.

## 😴 Recovery & Sleep
Evaluate sleep quality, rest days, energy levels. Risk of overtraining?

## 📈 Progress Indicators
Comment on trends in weight, mood, streak, and any PRs.

## 🎯 3 Priority Recommendations for Next Week
Give 3 specific, actionable improvements ranked by impact. Be concrete.

## 🔥 Motivational Closing
One powerful, personalized motivational message based on their actual data.

Keep each section concise (3-5 sentences). Be honest but encouraging."""

                resp = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1800
                )
                report_text = resp.choices[0].message.content

                st.markdown("---")
                st.markdown(f"### 📅 Weekly Report — {date.today().strftime('%B %d, %Y')}")
                st.markdown(report_text)
                st.markdown("---")

                # Download option
                st.download_button(
                    "⬇️ Download Report",
                    data=f"AI Fitness Report — {date.today()}\n\n{report_text}",
                    file_name=f"fitness_report_{date.today()}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"API Error: {e}")
user_email = st.session_state.get(
    "user_email",
    "Guest"
)

st.sidebar.success(
    f"👤 {user_email}"
)

