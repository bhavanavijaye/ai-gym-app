import os, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from utils.db import log_workout, get_workout_history, get_personal_records

# ── CSS ───────────────────────────────────────────────────────
_css = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles.css")
try:
    with open(_css) as f: st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except: pass

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/0_Login.py")

st.markdown("""
<div class="hero-section" style="padding:28px 40px">
    <div class="hero-title" style="font-size:2.4rem">🏋️ AI Workout Trainer</div>
    <div class="hero-subtitle">Log workouts · Track PRs · Analyse progress</div>
</div>""", unsafe_allow_html=True)

# ── Note about webcam ─────────────────────────────────────────
st.info("📱 **Pose detection** works best in the desktop app. Here you can log workouts manually and track all your progress.")

EXERCISES = [
    "Barbell Squat","Deadlift","Bench Press","Pull Up","Push Up",
    "Bicep Curl","Tricep Dip","Shoulder Press","Plank","Burpee",
    "Lunges","Leg Press","Lat Pulldown","Cable Row","Incline Press",
    "Romanian Deadlift","Hip Thrust","Arnold Press","Hammer Curl",
    "Box Jump","Mountain Climber","Russian Twist","Battle Rope",
    "Kettlebell Swing","Dips","Chin Up","Sprint","Running","Cycling",
]

MUSCLE_MAP = {
    "Barbell Squat":"Legs","Deadlift":"Back","Bench Press":"Chest",
    "Pull Up":"Back","Push Up":"Chest","Bicep Curl":"Arms",
    "Tricep Dip":"Arms","Shoulder Press":"Shoulders","Plank":"Core",
    "Burpee":"Full Body","Lunges":"Legs","Leg Press":"Legs",
    "Lat Pulldown":"Back","Cable Row":"Back","Incline Press":"Chest",
    "Romanian Deadlift":"Legs","Hip Thrust":"Legs","Arnold Press":"Shoulders",
    "Hammer Curl":"Arms","Box Jump":"Legs","Mountain Climber":"Core",
    "Russian Twist":"Core","Battle Rope":"Full Body","Kettlebell Swing":"Full Body",
    "Dips":"Chest","Chin Up":"Back","Sprint":"Cardio","Running":"Cardio","Cycling":"Cardio",
}

col_log, col_stats = st.columns([1, 1.5])

# ── LOG WORKOUT ───────────────────────────────────────────────
with col_log:
    st.subheader("📝 Log a Set")

    exercise = st.selectbox("Exercise", EXERCISES)
    muscle   = MUSCLE_MAP.get(exercise, "Full Body")
    st.caption(f"💪 Muscle group: **{muscle}**")

    c1, c2 = st.columns(2)
    with c1:
        sets     = st.number_input("Sets",       1, 10, 3)
        reps     = st.number_input("Reps",        1, 50, 10)
        weight   = st.number_input("Weight (kg)", 0.0, 500.0, 0.0, 2.5)
    with c2:
        duration = st.number_input("Duration (min)", 5, 180, 45)
        score    = st.slider("Performance (1-10)", 1.0, 10.0, 8.0, 0.5)
        notes    = st.text_area("Notes", height=68, placeholder="How did it feel?")

    # Estimate calories (MET-based)
    MET = {"Cardio":9.0,"Legs":7.0,"Back":6.5,"Chest":5.5,
           "Shoulders":5.5,"Arms":3.5,"Core":4.5,"Full Body":8.0}
    met_val  = MET.get(muscle, 6.0)
    # Use a default 70kg if no profile
    try:
        from utils.db import get_profile
        profile  = get_profile() or {}
        body_wt  = profile.get("weight_kg", 70)
    except Exception:
        body_wt  = 70
    est_cal = round(met_val * body_wt * (duration / 60), 1)

    st.metric("🔥 Estimated Calories", f"{est_cal} kcal")

    if st.button("✅ Log Workout", type="primary", use_container_width=True):
        log_workout(exercise, reps, sets, est_cal, score, weight, score, notes)
        st.success(f"✅ {sets}×{reps} {exercise} logged · {est_cal} kcal")
        st.rerun()

    st.divider()
    st.subheader("🏆 Personal Records")
    prs = get_personal_records()
    if not prs.empty:
        prs.columns = ["Exercise", "Best (kg)", "Date"]
        st.dataframe(prs, use_container_width=True, hide_index=True)
    else:
        st.info("Log workouts with weight to track PRs")

# ── ANALYTICS ─────────────────────────────────────────────────
with col_stats:
    st.subheader("📊 Workout Analytics")
    df = get_workout_history(60)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        tab1, tab2, tab3 = st.tabs(["📈 Calories", "💪 Volume", "📋 History"])

        with tab1:
            daily = df.groupby("date")["calories"].sum().reset_index()
            fig = px.area(daily, x="date", y="calories",
                          color_discrete_sequence=["#06b6d4"],
                          labels={"calories":"Calories Burned"})
            fig.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)",
                              font_color="white", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
            total = df["calories"].sum()
            avg   = df.groupby("date")["calories"].sum().mean()
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Burned",   f"{total:.0f} kcal")
            c2.metric("Avg per Session",f"{avg:.0f} kcal")
            c3.metric("Total Sessions", len(df))

        with tab2:
            df["volume"] = df["sets"] * df["reps"]
            vol = df.groupby("exercise")["volume"].sum().sort_values(ascending=True).reset_index()
            fig2 = px.bar(vol, y="exercise", x="volume", orientation="h",
                          color="volume", color_continuous_scale="Blues",
                          labels={"volume":"Total Volume (sets×reps)"})
            fig2.update_layout(height=350, plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)",
                               font_color="white", coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            show = df[["date","exercise","sets","reps","weight_kg","calories","form_score"]].copy()
            show["date"] = show["date"].dt.strftime("%b %d")
            show.columns = ["Date","Exercise","Sets","Reps","Weight(kg)","Cal","Score"]
            for c in ["Weight(kg)","Cal","Score"]:
                show[c] = show[c].round(1)
            st.dataframe(show.head(20), use_container_width=True, hide_index=True)
    else:
        st.info("No workouts yet — log your first session!")

# ── HEATMAP ───────────────────────────────────────────────────
st.divider()
st.subheader("📅 Training Heatmap — Last 60 Days")
df_all = get_workout_history(60)
if not df_all.empty:
    df_all["date"]    = pd.to_datetime(df_all["date"])
    df_all["week"]    = df_all["date"].dt.isocalendar().week.astype(str)
    df_all["weekday"] = df_all["date"].dt.day_name()
    hm = df_all.groupby(["week","weekday"]).size().reset_index(name="sessions")
    day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    hm["weekday"] = pd.Categorical(hm["weekday"], categories=day_order, ordered=True)
    fig3 = px.density_heatmap(hm, x="week", y="weekday", z="sessions",
                               color_continuous_scale="Blues")
    fig3.update_layout(height=250, plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                       margin=dict(t=10,b=10), xaxis_title="Week", yaxis_title="")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Log workouts to see your training heatmap")
