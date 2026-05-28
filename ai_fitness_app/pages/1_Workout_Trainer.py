import streamlit as st
import cv2
import time
import av
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from streamlit_webrtc import webrtc_streamer, VideoTransformerBase

from utils.sidebar import show_sidebar
from utils.voice import autoplay_audio

from utils.pose_utils import (
    process_frame,
    MEDIAPIPE_OK,
    EXERCISE_GUIDES,
    EXERCISE_HANDLERS,
    CALORIES_PER_REP,
    get_avg_form_score
)

from utils.db import (
    log_workout,
    get_workout_history,
    get_exercise_progress,
    get_personal_records,
    log_personal_record
)

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Workout Trainer",
    page_icon="🏋️",
    layout="wide"
)

# =========================
# SESSION
# =========================

if "user_email" not in st.session_state:
    st.session_state.user_email = "Guest User"

if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")

show_sidebar()

# =========================
# PAGE TITLE
# =========================

st.title("🏋️ AI Workout Trainer")

st.markdown(
    "Real-time pose detection, rep counting, and form scoring"
)

# =========================
# SESSION STATE
# =========================

if "rep_state" not in st.session_state:
    st.session_state.rep_state = {
        "count": 0,
        "stage": None,
        "form_scores": []
    }

if "current_set" not in st.session_state:
    st.session_state.current_set = 1

if "rest_end" not in st.session_state:
    st.session_state.rest_end = None

if "session_log" not in st.session_state:
    st.session_state.session_log = []

# =========================
# SIDEBAR
# =========================

with st.sidebar:

    st.subheader("⚙️ Session Settings")

    exercise = st.selectbox(
        "Exercise",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title()
    )

    sets_target = st.number_input(
        "Target Sets",
        1,
        10,
        3
    )

    reps_target = st.number_input(
        "Target Reps",
        1,
        60,
        10
    )

    weight_kg = st.number_input(
        "Weight Used (kg)",
        0.0,
        300.0,
        0.0,
        step=2.5
    )

    rest_seconds = st.slider(
        "Rest Time (sec)",
        30,
        180,
        60
    )

    st.divider()

    st.subheader("📖 Exercise Guide")

    st.info(
        EXERCISE_GUIDES.get(exercise, "")
    )

# =========================
# LAYOUT
# =========================

col1, col2 = st.columns([2, 1])

# =========================
# RIGHT PANEL
# =========================

with col2:

    st.subheader("📊 Live Stats")

    m1, m2 = st.columns(2)

    m1.metric(
        "Set",
        f"{st.session_state.current_set}/{sets_target}"
    )

    m2.metric(
        "Reps",
        st.session_state.rep_state["count"]
    )

    progress = min(
        st.session_state.rep_state["count"] /
        max(reps_target, 1),
        1.0
    )

    st.progress(
        progress,
        text=f"{st.session_state.rep_state['count']}/{reps_target} reps"
    )

    avg_form = get_avg_form_score(
        st.session_state.rep_state
    )

    form_color = (
        "🟢"
        if avg_form >= 7
        else "🟡"
        if avg_form >= 4
        else "🔴"
    )

    st.metric(
        "Form Score",
        f"{form_color} {avg_form}/10"
    )

    if st.button(
        "🔄 Reset Counter",
        use_container_width=True
    ):

        st.session_state.rep_state = {
            "count": 0,
            "stage": None,
            "form_scores": []
        }

        st.rerun()

# =========================
# WEBCAM
# =========================

class PoseTransformer(VideoTransformerBase):

    def transform(self, frame):

        img = frame.to_ndarray(format="bgr24")

        processed, count, stage, feedback, form_score = process_frame(
            img,
            exercise,
            st.session_state.rep_state
        )

        st.session_state.rep_state["count"] = count
        st.session_state.rep_state["stage"] = stage

        return av.VideoFrame.from_ndarray(
            processed,
            format="bgr24"
        )

with col1:

    run = st.toggle(
        "▶ Start Webcam",
        value=False
    )

    if run:

        st.success("📷 Webcam Active")

        webrtc_streamer(
            key="workout",
            video_transformer_factory=PoseTransformer,
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )

    else:

        st.image(
            "https://placehold.co/700x480/0d1117/1D9E75?text=Start+Webcam",
            use_container_width=True
        )

        st.info(
            "Toggle webcam to begin AI pose tracking"
        )

# =========================
# HISTORY
# =========================

st.divider()

tab1, tab2 = st.tabs([
    "📅 Workout History",
    "📈 Progress"
])

with tab1:

    df = get_workout_history(30)

    if not df.empty:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No workouts logged yet")

with tab2:

    selected_ex = st.selectbox(
        "Select Exercise",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
        key="prog_ex"
    )

    prog_df = get_exercise_progress(selected_ex)

    if not prog_df.empty:

        prog_df["date"] = pd.to_datetime(
            prog_df["date"]
        )

        fig = px.line(
            prog_df,
            x="date",
            y="reps",
            title="Reps Progress"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info("No progress data yet")

# =========================
# USER
# =========================

st.sidebar.success(
    f"👤 {st.session_state.get('user_email', 'Guest User')}"
)
