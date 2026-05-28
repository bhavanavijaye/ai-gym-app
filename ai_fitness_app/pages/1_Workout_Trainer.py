import os, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from utils.db import log_workout, get_workout_history, get_personal_records
import cv2
import mediapipe as mp
import numpy as np

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
# ── CAMERA REP COUNTER ────────────────────────────────────────
st.subheader("📷 Live Rep Counter")

cam_exercise = st.selectbox("Select exercise for rep counting", 
    list(EXERCISE_ANGLES.keys()), key="cam_ex")

col_cam, col_counter = st.columns([2, 1])

with col_counter:
    st.markdown("### 🔢 Rep Counter")
    if "rep_count" not in st.session_state:
        st.session_state.rep_count = 0
    if "rep_stage" not in st.session_state:
        st.session_state.rep_stage = None

    rep_display = st.empty()
    angle_display = st.empty()
    stage_display = st.empty()

    rep_display.metric("Reps", st.session_state.rep_count)

    c1, c2 = st.columns(2)
    with c1:
        start_cam = st.button("▶ Start", type="primary", use_container_width=True)
    with c2:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.rep_count = 0
            st.session_state.rep_stage = None
            st.rerun()

    st.info(f"**{cam_exercise}**\nPosition yourself so your full body is visible.")

with col_cam:
    FRAME_WINDOW = st.empty()

    if start_cam:
        mp_pose = mp.solutions.pose
        mp_draw = mp.solutions.drawing_utils

        config = EXERCISE_ANGLES[cam_exercise]
        j1, j2, j3 = config["joints"]
        down_thresh = config["down"]
        up_thresh   = config["up"]

        cap = cv2.VideoCapture(0)
        stop_btn = st.button("⏹ Stop Camera", key="stop_cam")

        with mp_pose.Pose(min_detection_confidence=0.6,
                          min_tracking_confidence=0.6) as pose:
            while cap.isOpened() and not stop_btn:
                ret, frame = cap.read()
                if not ret:
                    st.warning("Camera not accessible.")
                    break

                frame = cv2.flip(frame, 1)
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                if result.pose_landmarks:
                    lm = result.pose_landmarks.landmark

                    # Get landmark coords (use LEFT side)
                    def get_coord(name):
                        idx = LANDMARK_MAP[name][0].value
                        l = lm[idx]
                        return [l.x, l.y]

                    try:
                        a = get_coord(j1)
                        b = get_coord(j2)
                        c = get_coord(j3)
                        angle = calculate_angle(a, b, c)

                        # Rep logic
                        if angle > down_thresh:
                            st.session_state.rep_stage = "down"
                        if angle < up_thresh and st.session_state.rep_stage == "down":
                            st.session_state.rep_stage = "up"
                            st.session_state.rep_count += 1

                        # Draw on frame
                        h, w = frame.shape[:2]
                        bx, by = int(b[0]*w), int(b[1]*h)
                        cv2.putText(frame, f"{int(angle)}°",
                            (bx-30, by-15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0,255,255), 2)

                        # HUD overlay
                        cv2.rectangle(frame, (0,0), (220,80), (0,0,0), -1)
                        cv2.putText(frame, f"Reps: {st.session_state.rep_count}",
                            (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
                        cv2.putText(frame, f"Stage: {st.session_state.rep_stage or '-'}",
                            (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

                        rep_display.metric("Reps", st.session_state.rep_count)
                        angle_display.metric("Joint Angle", f"{int(angle)}°")
                        stage_display.caption(f"Stage: {st.session_state.rep_stage or '-'}")

                    except Exception:
                        pass

                    mp_draw.draw_landmarks(
                        frame, result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=3),
                        mp_draw.DrawingSpec(color=(0,100,255), thickness=2),
                    )

                FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                                   channels="RGB", use_container_width=True)

        cap.release()

st.divider()
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
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180 else angle

EXERCISE_ANGLES = {
    "Bicep Curl":       {"joints": ("shoulder","elbow","wrist"),  "down": 160, "up": 40},
    "Push Up":          {"joints": ("shoulder","elbow","wrist"),  "down": 160, "up": 90},
    "Barbell Squat":    {"joints": ("hip","knee","ankle"),        "down": 90,  "up": 160},
    "Lunges":           {"joints": ("hip","knee","ankle"),        "down": 90,  "up": 160},
    "Shoulder Press":   {"joints": ("elbow","shoulder","hip"),    "down": 90,  "up": 160},
    "Hammer Curl":      {"joints": ("shoulder","elbow","wrist"),  "down": 160, "up": 40},
    "Tricep Dip":       {"joints": ("shoulder","elbow","wrist"),  "down": 90,  "up": 160},
}

LANDMARK_MAP = {
    "shoulder": (mp.solutions.pose.PoseLandmark.LEFT_SHOULDER,  mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER),
    "elbow":    (mp.solutions.pose.PoseLandmark.LEFT_ELBOW,     mp.solutions.pose.PoseLandmark.RIGHT_ELBOW),
    "wrist":    (mp.solutions.pose.PoseLandmark.LEFT_WRIST,     mp.solutions.pose.PoseLandmark.RIGHT_WRIST),
    "hip":      (mp.solutions.pose.PoseLandmark.LEFT_HIP,       mp.solutions.pose.PoseLandmark.RIGHT_HIP),
    "knee":     (mp.solutions.pose.PoseLandmark.LEFT_KNEE,      mp.solutions.pose.PoseLandmark.RIGHT_KNEE),
    "ankle":    (mp.solutions.pose.PoseLandmark.LEFT_ANKLE,     mp.solutions.pose.PoseLandmark.RIGHT_ANKLE),
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
