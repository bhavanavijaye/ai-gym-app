import streamlit as st # pyright: ignore[reportMissingImports]
import cv2 # pyright: ignore[reportMissingImports]
import time
from utils.sidebar import show_sidebar
from utils.voice import autoplay_audio
if "user_email" not in st.session_state:
    st.session_state.user_email = "Guest User"
show_sidebar()

if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
from utils.pose_utils import (
    process_frame, MEDIAPIPE_OK, EXERCISE_GUIDES,
    EXERCISE_HANDLERS, CALORIES_PER_REP, get_avg_form_score
)
from utils.db import (
    log_workout, get_workout_history, get_exercise_progress,
    get_personal_records, log_personal_record
)
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]

st.set_page_config(page_title="Workout Trainer", page_icon="🏋️", layout="wide")
st.title("🏋️ AI Workout Trainer")
st.markdown("Real-time pose detection, rep counting, and **form scoring** across 8 exercises")



# ── Session state ──────────────────────────────────────────────────────────────
if "rep_state" not in st.session_state:
    st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
if "current_set" not in st.session_state:
    st.session_state.current_set = 1
if "rest_end" not in st.session_state:
    st.session_state.rest_end = None
if "session_log" not in st.session_state:
    st.session_state.session_log = []

# ── Sidebar settings ───────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Session Settings")
    exercise = st.selectbox(
        "Exercise",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title()
    )
    sets_target = st.number_input("Target Sets", 1, 10, 3)
    reps_target = st.number_input("Target Reps per Set", 1, 60, 10)
    weight_kg = st.number_input("Weight Used (kg)", 0.0, 300.0, 0.0, step=2.5,
                                 help="Enter 0 for bodyweight exercises")
    rest_seconds = st.slider("Rest Between Sets (sec)", 30, 180, 60)

    st.divider()
    st.subheader("📖 Exercise Guide")
    st.info(EXERCISE_GUIDES.get(exercise, ""))

    st.divider()
    st.subheader("🏆 Personal Records")
    prs = get_personal_records()
    if not prs.empty:
        st.dataframe(prs.rename(columns={
            "exercise": "Exercise", "best_weight": "Best (kg)", "date": "Date"
        }), use_container_width=True, hide_index=True)
    else:
        st.caption("No PRs yet — start lifting!")

# ── Main layout ────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("📊 Live Stats")

    m1, m2 = st.columns(2)
    m1.metric("Set", f"{st.session_state.current_set}/{sets_target}")
    m2.metric("Reps", st.session_state.rep_state["count"])

    progress = min(st.session_state.rep_state["count"] / max(reps_target, 1), 1.0)
    st.progress(progress, text=f"{st.session_state.rep_state['count']}/{reps_target} reps")

    avg_form = get_avg_form_score(st.session_state.rep_state)
    form_color = "🟢" if avg_form >= 7 else "🟡" if avg_form >= 4 else "🔴"
    st.metric("Avg Form Score", f"{form_color} {avg_form}/10")

    # ── Rest timer ─────────────────────────────────────────────────────────────
    if st.session_state.rest_end:
        remaining = st.session_state.rest_end - time.time()
        if remaining > 0:
            rest_pct = remaining / rest_seconds
            st.warning(f"⏱️ Rest: **{int(remaining)}s** remaining")
            st.progress(rest_pct)
        else:
            st.session_state.rest_end = None
            st.success("✅ Rest complete! Start your next set.")

    st.divider()

    # ── Set controls ───────────────────────────────────────────────────────────
    if st.button("➕ Next Set (Start Rest Timer)", use_container_width=True):
        reps_done = st.session_state.rep_state["count"]
        cal = reps_done * CALORIES_PER_REP.get(exercise, 5)
        form = get_avg_form_score(st.session_state.rep_state)
        st.session_state.session_log.append({
            "set": st.session_state.current_set,
            "exercise": exercise,
            "reps": reps_done,
            "form": form,
            "cal": cal
        })
        st.session_state.current_set += 1
        st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.rest_end = time.time() + rest_seconds
        st.rerun()

    if st.button("✅ Log Full Workout", use_container_width=True, type="primary"):
        reps = st.session_state.rep_state["count"]
        cal = reps * CALORIES_PER_REP.get(exercise, 5)
        form = get_avg_form_score(st.session_state.rep_state)
        total_sets = st.session_state.current_set

        log_workout(exercise, reps, total_sets, cal, 8.5,
                    weight_kg=weight_kg, form_score=form)

        # Check for PR
        prs_df = get_personal_records()
        existing = prs_df[prs_df["exercise"] == exercise]["best_weight"].values
        if weight_kg > 0 and (len(existing) == 0 or weight_kg > existing[0]):
            st.balloons()
            st.success(f"🏆 NEW PR! {weight_kg}kg on {exercise.replace('_',' ').title()}!")

        st.success(f"✅ Logged: {reps} reps × {total_sets} sets · {cal} cal · Form {form}/10")
        st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.current_set = 1
        st.session_state.session_log = []
        st.session_state.rest_end = None
        st.rerun()

    if st.button("🔄 Reset Counter", use_container_width=True):
        st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.rest_end = None
        st.rerun()

    # ── Session log ────────────────────────────────────────────────────────────
    if st.session_state.session_log:
        st.divider()
        st.subheader("📋 This Session")
        log_df = pd.DataFrame(st.session_state.session_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

with col1:
    run = st.toggle("▶ Start Webcam", value=False)
    frame_placeholder = st.empty()
    feedback_placeholder = st.empty()

    if run:
        if not MEDIAPIPE_OK:
            st.error("Fix MediaPipe first")
        else:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("❌ Cannot open webcam. Check camera.")
            else:
                st.info("Webcam running — toggle off to stop")
                while run:
                    ret, frame = cap.read()
                    if not ret:
                        st.warning("Frame read failed")
                        break
                    processed, count, stage, feedback, form_score = process_frame(
                        frame, exercise, st.session_state.rep_state
                    )
                    st.session_state.rep_state["count"] = count
                    st.session_state.rep_state["stage"] = stage

                    frame_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                    feedback_placeholder.info(f"**Feedback:** {feedback}")

                    if not st.session_state.get("_run_webcam", True):
                        break
                cap.release()
    else:
        frame_placeholder.image(
            "https://placehold.co/700x480/0d1117/1D9E75?text=Toggle+Start+Webcam",
            use_container_width=True
        )
        feedback_placeholder.info("Toggle **▶ Start Webcam** to begin real-time pose detection")

# ── Progress charts ────────────────────────────────────────────────────────────
st.divider()
tab1, tab2 = st.tabs(["📅 Workout History", "📈 Exercise Progress"])

with tab1:
    df = get_workout_history(30)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No workouts logged yet — complete a session above!")

with tab2:
    selected_ex = st.selectbox(
        "Select exercise to chart progress",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
        key="prog_ex"
    )
    prog_df = get_exercise_progress(selected_ex)
    if not prog_df.empty:
        prog_df["date"] = pd.to_datetime(prog_df["date"])
        col_r, col_w = st.columns(2)
        with col_r:
            fig_r = px.line(prog_df, x="date", y="reps",
                            title="Reps Over Time",
                            color_discrete_sequence=["#1D9E75"])
            fig_r.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                 paper_bgcolor="rgba(0,0,0,0)", height=220)
            st.plotly_chart(fig_r, use_container_width=True)
        with col_w:
            if prog_df["weight_kg"].sum() > 0:
                fig_w = px.line(prog_df, x="date", y="weight_kg",
                                title="Weight Used (kg)",
                                color_discrete_sequence=["#378ADD"])
                fig_w.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                     paper_bgcolor="rgba(0,0,0,0)", height=220)
                st.plotly_chart(fig_w, use_container_width=True)
            else:
                fig_f = px.line(prog_df, x="date", y="form_score",
                                title="Form Score Trend",
                                color_discrete_sequence=["#EF9F27"])
                fig_f.add_hline(y=7, line_dash="dash",
                                annotation_text="Good Form ≥ 7",
                                line_color="rgba(100,200,100,0.5)")
                fig_f.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                     paper_bgcolor="rgba(0,0,0,0)", height=220)
                st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.info(f"No data yet for {selected_ex.replace('_', ' ').title()}")
user_email = st.session_state.get(
    "user_email",
    "Guest"
)

st.sidebar.success(
   f"👤 {st.session_state.get('user_email', 'Guest User')}"
)

