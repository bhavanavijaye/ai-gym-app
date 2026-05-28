import streamlit as st
import av
import threading
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

from utils.pose_utils import (
    process_frame,
    MEDIAPIPE_OK,
    EXERCISE_GUIDES,
    EXERCISE_HANDLERS,
    CALORIES_PER_REP,
    get_avg_form_score,
)
from utils.db import (
    log_workout,
    get_workout_history,
    get_exercise_progress,
    get_personal_records,
    log_personal_record,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Workout Trainer",
    page_icon="🏋️",
    layout="wide",
)

# ─────────────────────────────────────────────
# AUTH GUARD  (remove if you have no login page)
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True          # allow direct access in dev
if "user_email" not in st.session_state:
    st.session_state.user_email = "Guest User"

# ─────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────
if "rep_state" not in st.session_state:
    st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
if "current_set" not in st.session_state:
    st.session_state.current_set = 1
if "rest_end" not in st.session_state:
    st.session_state.rest_end = None
if "session_log" not in st.session_state:
    st.session_state.session_log = []

# ─────────────────────────────────────────────
# STUN / TURN  ← THIS IS THE CORE FIX FOR RENDER
# ─────────────────────────────────────────────
RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            {"urls": ["stun:stun3.l.google.com:19302"]},
            {"urls": ["stun:stun4.l.google.com:19302"]},
        ]
    }
)

# ─────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────
st.title("🏋️ AI Workout Trainer")
st.markdown("Real-time **pose detection**, rep counting, and form scoring")

if not MEDIAPIPE_OK:
    st.error(
        "❌ MediaPipe not loaded. Run: `pip uninstall mediapipe -y && pip install mediapipe==0.10.14`"
    )

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Session Settings")

    exercise = st.selectbox(
        "Exercise",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
    )
    sets_target  = st.number_input("Target Sets",         1,  10,  3)
    reps_target  = st.number_input("Target Reps per Set", 1,  60, 10)
    weight_kg    = st.number_input("Weight Used (kg)",    0.0, 300.0, 0.0, step=2.5)
    rest_seconds = st.slider("Rest Between Sets (sec)", 30, 180, 60)

    st.divider()
    st.subheader("📖 Exercise Guide")
    st.info(EXERCISE_GUIDES.get(exercise, ""))

    st.divider()
    st.subheader("🏆 Personal Records")
    prs = get_personal_records()
    if not prs.empty:
        st.dataframe(
            prs.rename(columns={"exercise": "Exercise", "best_weight": "Best (kg)", "date": "Date"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No PRs yet — start lifting!")

    st.divider()
    st.caption(f"👤 {st.session_state.get('user_email', 'Guest')}")

# ─────────────────────────────────────────────
# VIDEO PROCESSOR  ← FIXED: VideoProcessorBase + recv()
#
# ⚠️  st.session_state cannot be written from a
#     background thread.  We use instance variables
#     and a lock, then read them in the main thread.
# ─────────────────────────────────────────────
class PoseProcessor(VideoProcessorBase):
    """Thread-safe pose processor."""

    def __init__(self):
        self._lock       = threading.Lock()
        self._rep_count  = 0
        self._stage      = None
        self._form_scores = []
        self._feedback   = "Waiting for pose…"
        self._form_score = 0.0
        # exercise is read from session state ONCE at construction;
        # it updates when the user changes the selectbox and the
        # streamer is restarted automatically by streamlit-webrtc.
        self._exercise   = "bicep_curl"

    # Public setters called from the main thread before each render
    def set_exercise(self, ex: str):
        with self._lock:
            self._exercise = ex

    def get_state(self):
        with self._lock:
            return {
                "count":       self._rep_count,
                "stage":       self._stage,
                "form_scores": list(self._form_scores),
                "feedback":    self._feedback,
                "form_score":  self._form_score,
            }

    def reset(self):
        with self._lock:
            self._rep_count  = 0
            self._stage      = None
            self._form_scores = []
            self._feedback   = "Counter reset"
            self._form_score = 0.0

    # ── FIXED: recv() instead of transform() ──────────────────────────────
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        with self._lock:
            ex      = self._exercise
            r_state = {
                "count":       self._rep_count,
                "stage":       self._stage,
                "form_scores": self._form_scores,
            }

        processed, count, stage, feedback, form_score = process_frame(
            img, ex, r_state
        )

        with self._lock:
            self._rep_count   = count
            self._stage       = stage
            self._form_scores = r_state.get("form_scores", [])
            self._feedback    = feedback
            self._form_score  = form_score

        return av.VideoFrame.from_ndarray(processed, format="bgr24")


# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

# ──────────────── RIGHT: LIVE STATS ──────────
with col2:
    st.subheader("📊 Live Stats")

    m1, m2 = st.columns(2)
    m1.metric("Set",  f"{st.session_state.current_set}/{sets_target}")
    m2.metric("Reps", st.session_state.rep_state["count"])

    progress = min(
        st.session_state.rep_state["count"] / max(reps_target, 1), 1.0
    )
    st.progress(
        progress,
        text=f"{st.session_state.rep_state['count']}/{reps_target} reps",
    )

    avg_form   = get_avg_form_score(st.session_state.rep_state)
    form_emoji = "🟢" if avg_form >= 7 else "🟡" if avg_form >= 4 else "🔴"
    st.metric("Avg Form Score", f"{form_emoji} {avg_form}/10")

    # ── Rest timer ────────────────────────────────────────────────────────
    if st.session_state.rest_end:
        remaining = st.session_state.rest_end - time.time()
        if remaining > 0:
            st.warning(f"⏱️ Rest: **{int(remaining)}s** remaining")
            st.progress(remaining / rest_seconds)
        else:
            st.session_state.rest_end = None
            st.success("✅ Rest done! Start your next set.")

    st.divider()

    # ── Controls ──────────────────────────────────────────────────────────
    if st.button("➕ Next Set (Start Rest Timer)", use_container_width=True):
        reps_done = st.session_state.rep_state["count"]
        cal  = reps_done * CALORIES_PER_REP.get(exercise, 5)
        form = get_avg_form_score(st.session_state.rep_state)
        st.session_state.session_log.append(
            {"set": st.session_state.current_set, "exercise": exercise,
             "reps": reps_done, "form": form, "cal": cal}
        )
        st.session_state.current_set += 1
        st.session_state.rep_state   = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.rest_end    = time.time() + rest_seconds
        st.rerun()

    if st.button("✅ Log Full Workout", use_container_width=True, type="primary"):
        reps  = st.session_state.rep_state["count"]
        cal   = reps * CALORIES_PER_REP.get(exercise, 5)
        form  = get_avg_form_score(st.session_state.rep_state)
        total = st.session_state.current_set

        log_workout(exercise, reps, total, cal, 8.5,
                    weight_kg=weight_kg, form_score=form)

        # PR check
        prs_df   = get_personal_records()
        existing = prs_df[prs_df["exercise"] == exercise]["best_weight"].values
        if weight_kg > 0 and (len(existing) == 0 or weight_kg > existing[0]):
            st.balloons()
            st.success(f"🏆 NEW PR! {weight_kg}kg on {exercise.replace('_',' ').title()}!")

        st.success(f"✅ Logged: {reps} reps × {total} sets · {cal} cal · Form {form}/10")
        st.session_state.rep_state   = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.current_set = 1
        st.session_state.session_log = []
        st.session_state.rest_end    = None
        st.rerun()

    if st.button("🔄 Reset Counter", use_container_width=True):
        st.session_state.rep_state = {"count": 0, "stage": None, "form_scores": []}
        st.session_state.rest_end  = None
        st.rerun()

    # ── Session log ───────────────────────────────────────────────────────
    if st.session_state.session_log:
        st.divider()
        st.subheader("📋 This Session")
        st.dataframe(
            pd.DataFrame(st.session_state.session_log),
            use_container_width=True, hide_index=True,
        )

# ──────────────── LEFT: WEBCAM ───────────────
with col1:
    st.subheader("📷 Live Camera")

    # ── FIXED: RTCConfiguration + VideoProcessorBase ──────────────────────
    ctx = webrtc_streamer(
        key=f"workout-{exercise}",          # key changes → processor restarts on exercise change
        video_processor_factory=PoseProcessor,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    # ── Sync processor ↔ session state ───────────────────────────────────
    if ctx.video_processor:
        # Push current exercise into the processor (thread-safe)
        ctx.video_processor.set_exercise(exercise)

        # Pull rep count / form back into session state
        state = ctx.video_processor.get_state()
        st.session_state.rep_state["count"]       = state["count"]
        st.session_state.rep_state["stage"]       = state["stage"]
        st.session_state.rep_state["form_scores"] = state["form_scores"]

        # Live feedback banner
        st.info(f"**Feedback:** {state['feedback']}")

        # Auto-refresh every ~0.5 s while streaming
        time.sleep(0.5)
        st.rerun()

    elif not ctx.state.playing:
        st.image(
            "https://placehold.co/700x480/0d1117/1D9E75?text=Click+START+to+begin",
            use_container_width=True,
        )
        st.caption(
            "👆 Click **START** above, then allow camera access in your browser."
        )

    # ── Connection help ───────────────────────────────────────────────────
    with st.expander("📡 Camera not connecting? Read this"):
        st.markdown("""
**Common fixes:**

1. **Allow camera** in your browser (address bar → 🔒 → Camera → Allow)
2. **HTTPS required** — WebRTC only works over HTTPS.  
   Render deploys with HTTPS by default ✅
3. **Firewall/VPN** — disable for the domain while testing
4. **Try Chrome or Edge** (best WebRTC support)
5. If still failing, scroll down to the **Snapshot Mode** fallback below ↓
        """)

# ─────────────────────────────────────────────
# FALLBACK: SNAPSHOT / UPLOAD MODE
# ─────────────────────────────────────────────
with st.expander("📸 Alternative: Upload a Photo for Form Analysis"):
    st.markdown("Use this if the live webcam doesn't work in your environment.")
    uploaded = st.file_uploader(
        "Upload a workout photo (JPG/PNG)", type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        import numpy as np
        import cv2
        from PIL import Image
        img = np.array(Image.open(uploaded).convert("RGB"))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        dummy_state = {"count": 0, "stage": None, "form_scores": []}
        processed, count, stage, feedback, form_score = process_frame(
            img_bgr, exercise, dummy_state
        )
        result_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
        st.image(result_rgb, caption=f"Form Score: {form_score}/10 — {feedback}",
                 use_container_width=True)
        st.metric("Pose Form Score", f"{form_score}/10")
        st.info(f"**AI Feedback:** {feedback}")

# ─────────────────────────────────────────────
# PROGRESS CHARTS
# ─────────────────────────────────────────────
st.divider()
tab1, tab2 = st.tabs(["📅 Workout History", "📈 Exercise Progress"])

with tab1:
    df = get_workout_history(30)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No workouts logged yet — complete a session above!")

with tab2:
    sel_ex = st.selectbox(
        "Select exercise to chart",
        list(EXERCISE_HANDLERS.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
        key="prog_ex",
    )
    prog_df = get_exercise_progress(sel_ex)
    if not prog_df.empty:
        prog_df["date"] = pd.to_datetime(prog_df["date"])
        c1, c2 = st.columns(2)
        with c1:
            fig_r = px.line(prog_df, x="date", y="reps",
                            title="Reps Over Time",
                            color_discrete_sequence=["#1D9E75"])
            fig_r.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)", height=250)
            st.plotly_chart(fig_r, use_container_width=True)
        with c2:
            if "form_score" in prog_df.columns and prog_df["form_score"].sum() > 0:
                fig_f = px.line(prog_df, x="date", y="form_score",
                                title="Form Score Trend",
                                color_discrete_sequence=["#EF9F27"])
                fig_f.add_hline(y=7, line_dash="dash",
                                annotation_text="Good Form ≥ 7",
                                line_color="rgba(100,200,100,0.5)")
                fig_f.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                    paper_bgcolor="rgba(0,0,0,0)", height=250)
                st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.info(f"No data for {sel_ex.replace('_', ' ').title()} yet.")
