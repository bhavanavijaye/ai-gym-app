import streamlit as st # pyright: ignore[reportMissingImports]
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # pyright: ignore[reportMissingImports]
import plotly.subplots as sp # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
import numpy as np # pyright: ignore[reportMissingImports]
from datetime import date, timedelta
from utils.db import log_habit, get_habit_history, log_sleep, get_sleep_history, get_today_water
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
st.set_page_config(page_title="Habit Tracker", page_icon="📊", layout="wide")
st.title("📊 AI Fitness Habit Tracker")
st.markdown("Track consistency, mood, sleep & energy — predict skip risk before it happens")
from utils.sidebar import show_sidebar
col1, col2 = st.columns([1, 2])
show_sidebar()
# ── Left: daily check-in ───────────────────────────────────────────────────────
with col1:
    st.subheader("✅ Today's Check-in")

    completed = st.checkbox("Did you complete your workout today?")

    mood = st.slider("How do you feel today?", 1, 10, 7,
                     help="1=Terrible | 5=Okay | 10=Amazing")
    mood_labels = {
        1: "😫 Terrible", 2: "😔 Bad", 3: "😞 Low", 4: "😐 Meh",
        5: "🙂 Okay", 6: "😊 Good", 7: "😃 Great",
        8: "🤩 Awesome", 9: "🏆 Excellent", 10: "🔥 On Fire!"
    }
    st.caption(f"**Mood:** {mood_labels.get(mood, '')}")

    energy_level = st.slider("Energy level", 1, 10, 7,
                              help="How energetic did you feel during the workout?")

    notes = st.text_area("Session notes", placeholder="PRs, pain, energy thoughts...", height=80)

    st.divider()
    st.subheader("😴 Sleep Logger")
    sleep_hours = st.slider("Hours slept last night", 0.0, 12.0, 7.0, step=0.5)
    sleep_quality = st.slider("Sleep quality", 1, 10, 7,
                               help="1=Terrible | 10=Perfect")
    bedtime = st.text_input("Bedtime (optional)", placeholder="e.g. 22:30")
    wake_time = st.text_input("Wake time (optional)", placeholder="e.g. 06:00")

    if st.button("💾 Save Today's Log", type="primary", use_container_width=True):
        water_today = get_today_water()
        log_habit(1 if completed else 0, mood, notes, sleep_hours, energy_level, water_today)
        log_sleep(sleep_hours, sleep_quality, bedtime, wake_time)
        if completed:
            st.success("🏆 Logged! Keep the streak going!")
            st.balloons()
        else:
            st.info("Logged. Rest days matter too. Come back stronger!")

    # ── Skip risk predictor ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🧠 Smart Skip Predictor")
    df_h = get_habit_history()
    if not df_h.empty and len(df_h) >= 3:
        recent_7 = df_h.head(7)
        skip_count = int(len(recent_7) - recent_7["completed"].sum())
        skip_prob = skip_count / len(recent_7) * 100

        # Factor in low energy + mood
        avg_mood_7 = recent_7["mood"].mean() if "mood" in recent_7.columns else 5
        avg_energy_7 = recent_7["energy_level"].mean() if "energy_level" in recent_7.columns else 5

        # Composite risk
        mood_risk = max(0, (5 - avg_mood_7) * 5)
        energy_risk = max(0, (5 - avg_energy_7) * 5)
        composite_risk = (skip_prob * 0.6 + mood_risk * 0.2 + energy_risk * 0.2)

        if composite_risk > 60:
            st.error(f"🚨 High risk ({composite_risk:.0f}%) — {skip_count} of last 7 missed + low energy/mood")
        elif composite_risk > 30:
            st.warning(f"⚠️ Moderate risk ({composite_risk:.0f}%) — You can do better!")
        else:
            st.success(f"✅ Low risk ({composite_risk:.0f}%) — You're crushing it!")

        # Mini 7-day bar
        streak_df = pd.DataFrame({
            "Day": list(range(1, len(recent_7) + 1)),
            "Done": recent_7["completed"].tolist()
        })
        fig_mini = px.bar(streak_df, x="Day", y="Done",
                          color="Done",
                          color_continuous_scale=["#E24B4A", "#1D9E75"],
                          title="Last 7 Days", height=180)
        fig_mini.update_layout(showlegend=False,
                               plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)",
                               coloraxis_showscale=False,
                               margin=dict(t=30, b=0))
        st.plotly_chart(fig_mini, use_container_width=True)
    else:
        st.info("Log 3+ days to unlock the predictor")

# ── Right: charts ──────────────────────────────────────────────────────────────
with col2:
    tab_h, tab_s, tab_c = st.tabs(["📈 History", "😴 Sleep Analysis", "🔥 Streak Calendar"])

    with tab_h:
        df_h = get_habit_history(30)
        if not df_h.empty:
            df_h["date"] = pd.to_datetime(df_h["date"])
            df_h = df_h.sort_values("date")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_h["date"], y=df_h["completed"],
                name="Workout Done",
                marker_color=["#1D9E75" if c else "#E24B4A" for c in df_h["completed"]],
                opacity=0.8
            ))
            fig.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["mood"],
                name="Mood (1-10)",
                line=dict(color="#378ADD", width=2),
                mode="lines+markers", yaxis="y2"
            ))
            if "energy_level" in df_h.columns:
                fig.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["energy_level"],
                    name="Energy (1-10)",
                    line=dict(color="#EF9F27", width=2, dash="dot"),
                    mode="lines+markers", yaxis="y2"
                ))
            fig.update_layout(
                yaxis=dict(title="Completed", range=[0, 1.5]),
                yaxis2=dict(title="Score 1-10", overlaying="y", side="right", range=[0, 10]),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=1.1), height=320
            )
            st.plotly_chart(fig, use_container_width=True)

            total = len(df_h)
            done = int(df_h["completed"].sum())
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Consistency", f"{done/total*100:.0f}%", f"{done}/{total} days")
            s2.metric("Avg Mood", f"{df_h['mood'].mean():.1f}/10")
            s3.metric("Total Workouts", done)
            if "energy_level" in df_h.columns:
                s4.metric("Avg Energy", f"{df_h['energy_level'].mean():.1f}/10")

            st.subheader("Recent Log")
            disp = df_h[["date", "completed", "mood", "energy_level"]].copy().tail(10)
            disp["date"] = disp["date"].dt.strftime("%b %d")
            disp["completed"] = disp["completed"].map({1: "✅", 0: "❌"})
            disp.columns = ["Date", "Done", "Mood", "Energy"]
            st.dataframe(disp, use_container_width=True, hide_index=True)
        else:
            st.info("Start logging to see your habit history!")

    with tab_s:
        sleep_df = get_sleep_history(30)
        if not sleep_df.empty:
            sleep_df["date"] = pd.to_datetime(sleep_df["date"])
            sleep_df = sleep_df.sort_values("date")

            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                x=sleep_df["date"], y=sleep_df["hours"],
                name="Sleep Hours",
                marker_color=["#1D9E75" if h >= 7 else "#EF9F27" if h >= 6 else "#E24B4A"
                               for h in sleep_df["hours"]]
            ))
            if "quality" in sleep_df.columns:
                fig_s.add_trace(go.Scatter(
                    x=sleep_df["date"], y=sleep_df["quality"],
                    name="Quality (1-10)",
                    line=dict(color="#9B59B6", width=2),
                    mode="lines+markers", yaxis="y2"
                ))
            fig_s.add_hline(y=7, line_dash="dash",
                            annotation_text="7h goal",
                            line_color="rgba(100,200,100,0.5)")
            fig_s.update_layout(
                yaxis=dict(title="Hours Slept"),
                yaxis2=dict(title="Quality 1-10", overlaying="y", side="right", range=[0, 10]),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=300, legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_s, use_container_width=True)

            avg_h = sleep_df["hours"].mean()
            avg_q = sleep_df["quality"].mean() if "quality" in sleep_df.columns else 0
            nights_ok = (sleep_df["hours"] >= 7).sum()

            ss1, ss2, ss3 = st.columns(3)
            ss1.metric("Avg Sleep", f"{avg_h:.1f}h", "✅ Good" if avg_h >= 7 else "⚠️ Low")
            ss2.metric("Avg Quality", f"{avg_q:.1f}/10")
            ss3.metric("7h+ Nights", f"{nights_ok}/{len(sleep_df)}")
        else:
            st.info("Log sleep from the check-in form to see analysis here.")

    with tab_c:
        st.subheader("🔥 Streak Calendar (GitHub-style)")
        df_cal = get_habit_history(90)
        if not df_cal.empty:
            df_cal["date"] = pd.to_datetime(df_cal["date"])
            # Build a 13-week heatmap
            end_date = date.today()
            start_date = end_date - timedelta(weeks=13)
            all_dates = pd.date_range(start=start_date, end=end_date)

            date_map = dict(zip(df_cal["date"].dt.date, df_cal["completed"]))
            grid_data = []
            for d in all_dates:
                week_num = (d - pd.Timestamp(start_date)).days // 7
                day_of_week = d.dayofweek  # 0=Mon
                completed_val = date_map.get(d.date(), -1)  # -1 = no data
                grid_data.append({
                    "week": week_num, "dow": day_of_week,
                    "date": d.date(), "completed": completed_val
                })
            grid_df = pd.DataFrame(grid_data)
            pivot = grid_df.pivot(index="dow", columns="week", values="completed")

            colorscale = [[0, "#1a1a2e"], [0.4, "#E24B4A"], [0.7, "#9FE1CB"], [1.0, "#1D9E75"]]
            fig_cal = go.Figure(go.Heatmap(
                z=pivot.values,
                colorscale=colorscale,
                showscale=False,
                zmin=-1, zmax=1,
            ))
            fig_cal.update_layout(
                yaxis=dict(tickmode="array",
                           tickvals=list(range(7)),
                           ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                xaxis=dict(showticklabels=False),
                height=220,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10)
            )
            st.plotly_chart(fig_cal, use_container_width=True)
            st.caption("🟢 Workout done  🔴 Missed  ⬛ No data")
        else:
            st.info("Log at least a week of habits to see the calendar.")