import streamlit as st # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # pyright: ignore[reportMissingImports]


from utils.db import (
    init_db,
    get_weekly_summary,
    get_body_stats_history,
    get_sleep_history,
    get_today_water
)

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Fitness OS",
    page_icon="💪",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# LOGIN CHECK
# ─────────────────────────────────────────────────────────────
if (
    "logged_in" not in st.session_state
    or
    not st.session_state["logged_in"]
):
    st.switch_page("pages/0_Login.py")

# ─────────────────────────────────────────────────────────────
# LOAD CSS
# ─────────────────────────────────────────────────────────────
with open("styles.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────
# INIT DATABASE
# ─────────────────────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────
summary = get_weekly_summary()

body_df = get_body_stats_history()
sleep_df = get_sleep_history(30)

# ─────────────────────────────────────────────────────────────
# RECOVERY SCORE
# ─────────────────────────────────────────────────────────────
mood = summary.get("avg_mood", 5)
sleep = min(summary.get("avg_sleep", 6), 9)
streak = min(summary.get("streak", 0), 7)

recovery = int(
    (mood / 10 * 40)
    + (sleep / 9 * 40)
    + (streak / 7 * 20)
)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
st.sidebar.title("💪 AI Fitness OS")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "🏋️ Workout Trainer",
        "🥗 Diet Coach",
        "🤖 AI Coach",
        "📊 Habit Tracker",
        "📏 Body Stats",
        "📅 Weekly Report"
    ]
)

if page == "🏋️ Workout Trainer":
    st.switch_page("pages/1_Workout_Trainer.py")

elif page == "🥗 Diet Coach":
    st.switch_page("pages/2_Diet_Coach.py")

elif page == "🤖 AI Coach":
    st.switch_page("pages/3_AI_Chatbot.py")

elif page == "📊 Habit Tracker":
    st.switch_page("pages/4_Habit_Tracker.py")

elif page == "📏 Body Stats":
    st.switch_page("pages/5_Body_Stats.py")

elif page == "📅 Weekly Report":
    st.switch_page("pages/7_Weekly_Report.py")

st.sidebar.markdown("---")

user_email = st.session_state.get(
    "user_email",
    "Guest"
)

st.sidebar.success(
    f"👤 {user_email}"
)

if st.sidebar.button("Logout"):

    st.session_state.clear()

    st.switch_page("pages/0_Login.py")

# ─────────────────────────────────────────────────────────────
# HERO SECTION
# ─────────────────────────────────────────────────────────────
# HERO SECTION
# =========================
# HERO SECTION
# =========================
st.markdown("""
<div class="hero-section">
    <div class="hero-title">💪 AI Fitness OS</div>
    <div class="hero-subtitle">Your intelligent AI-powered fitness ecosystem</div>
</div>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────────────────────
# ── METRIC CARDS ─────────────────────────────

col1, col2, col3, col4 = st.columns(4)

metrics = [
    ("🔥 Calories", "0 kcal"),
    ("💪 Workouts", "0"),
    ("😴 Sleep", "0h"),
    ("⚡ Recovery", "28/100")
]

for col, metric in zip(
    [col1, col2, col3, col4],
    metrics
):

    with col:

        st.markdown(f"""
        <div class="metric-card">
            <h3>{metric[0]}</h3>
            <h1>{metric[1]}</h1>
        </div>
        """, unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────
# AI ORB
# ─────────────────────────────────────────────────────────────
# =========================
# HERO SECTION
# =========================
st.markdown("""
<div class="ai-orb-container">
    <div class="ai-orb"></div>
    <div class="orb-text">AI Assistant Active</div>
</div>
""", unsafe_allow_html=True)
#──────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────
col_left, col_mid, col_right = st.columns([2, 2, 1])

# WEEKLY ACTIVITY
with col_left:

    st.subheader("📊 Weekly Activity")

    weekly = summary.get("weekly_data", [])

    if weekly:

        df = pd.DataFrame(weekly)

        fig = px.bar(
            df,
            x="day",
            y="calories",
            color="type",
            color_discrete_sequence=["#06b6d4", "#3b82f6"]
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=300
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "Complete your first workout to see analytics."
        )

# WEIGHT TREND
with col_mid:

    st.subheader("⚖️ Weight Trend")

    if not body_df.empty and "weight_kg" in body_df.columns:

        body_df["date"] = pd.to_datetime(body_df["date"])

        fig2 = px.line(
            body_df,
            x="date",
            y="weight_kg",
            color_discrete_sequence=["#06b6d4"]
        )

        fig2.update_traces(
            mode="lines+markers"
        )

        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=300
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    else:

        st.info(
            "Log body stats to track progress."
        )

# WATER TRACKER
with col_right:

    st.subheader("💧 Water")

    water_ml = get_today_water()

    water_goal = 2500

    fig_water = go.Figure(go.Indicator(
        mode="gauge+number",
        value=water_ml,
        number={
            "suffix": "ml"
        },
        gauge={
            "axis": {
                "range": [0, water_goal]
            },
            "bar": {
                "color": "#06b6d4"
            }
        }
    ))

    fig_water.update_layout(
        height=260,
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(
        fig_water,
        use_container_width=True
    )

# ─────────────────────────────────────────────────────────────
# SLEEP HISTORY
# ─────────────────────────────────────────────────────────────
st.subheader("😴 Sleep History")

if not sleep_df.empty:

    sleep_df["date"] = pd.to_datetime(
        sleep_df["date"]
    )

    fig_sleep = px.line(
        sleep_df,
        x="date",
        y="hours",
        color_discrete_sequence=["#22d3ee"]
    )

    fig_sleep.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=300
    )

    st.plotly_chart(
        fig_sleep,
        use_container_width=True
    )

else:

    st.info(
        "Log sleep data to view trends."
    )