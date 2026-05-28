"""
3_AI_Chatbot.py  —  Voice + Text AI Fitness Coach
Fixes vs original:
  • Groq client & user_context cached with st.cache_resource / st.cache_data
  • Streaming responses (characters appear as they generate, no full wait)
  • Voice mode only fires once — removed duplicate listen() blocks
  • Quick-question state handled cleanly before chat_input
  • autoplay_audio only called once per response
  • Lottie loaded with st.cache_data so it never re-fetches
"""

import streamlit as st # pyright: ignore[reportMissingImports]
from groq import Groq # pyright: ignore[reportMissingImports]
import os
from utils.sidebar import show_sidebar
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from utils.db import get_full_context_for_ai
show_sidebar()
load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Fitness Coach", page_icon="🤖", layout="wide")

# ── Guard: require login if you have a login system ───────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = True   # remove this line if you have real auth

# ── Cached resources (only created ONCE per session) ──────────────────────────
@st.cache_resource
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=api_key) if api_key else None

@st.cache_data(ttl=30)          # refresh user context at most every 30s
def get_user_context():
    try:
        return get_full_context_for_ai()
    except Exception:
        return "No fitness data logged yet."

@st.cache_data(ttl=3600)        # Lottie JSON — fetch once per hour
def load_lottie(url: str):
    try:
        import requests # pyright: ignore[reportMissingModuleSource]
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

# ── Check voice dependencies once ─────────────────────────────────────────────
@st.cache_resource
def voice_available():
    try:
        import sounddevice, faster_whisper
        return True
    except (OSError, ImportError):
        return False
VOICE_OK = voice_available()


if VOICE_OK:
    # show voice input button
else:
    st.info("🎙️ Voice input unavailable in cloud environment.")
GROQ_MODEL = "llama-3.1-8b-instant"
user_context = get_user_context()

SYSTEM_PROMPT = f"""You are FitBot, an expert AI personal trainer and nutritionist with 10+ years of experience.
You have access to the user's real fitness data shown below — use it to give PERSONALIZED advice.

{user_context}

You help users with:
- Personalized workout plans and exercise form advice
- Nutrition and diet guidance based on their logged meals
- Motivation and habit building
- Recovery and injury prevention
- Goal setting and progress analysis based on their actual data

Be encouraging, practical, and science-backed. Reference their actual data when relevant.
Keep responses concise but detailed. Use bullet points for lists. Use metric units.
When recommending exercises, mention proper form. Always end workout advice with a safety reminder."""

# ── Page header ────────────────────────────────────────────────────────────────
st.title("🤖 Virtual Gym Buddy")
st.markdown("Your **context-aware** AI fitness coach — knows your workouts, diet & progress!")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📊 What FitBot knows")
    with st.expander("View your data context"):
        st.code(user_context, language=None)

    st.divider()
    st.subheader("⚡ Quick Questions")
    quick_questions = [
        "Analyze my recent workout performance",
        "Is my diet on track for my goals?",
        "Give me a 10-minute home workout",
        "What should I eat before a workout?",
        "How do I break through a plateau?",
        "Best exercises for weight loss",
        "How much protein do I need daily?",
        "Motivate me — I want to skip today",
        "How to improve sleep for recovery?",
        "Am I overtraining? Check my streak",
        "Suggest a deload week plan",
        "How to fix bad posture",
    ]
    for q in quick_questions:
        if st.button(q, use_container_width=True, key=f"qq_{hash(q)}"):
            st.session_state["pending_prompt"] = q
            st.rerun()

    st.divider()
    col_clear, col_refresh = st.columns(2)
    with col_clear:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_refresh:
        if st.button("🔄 Refresh data", use_container_width=True,
                     help="Reload your latest fitness stats"):
            get_user_context.clear()
            st.rerun()

    st.divider()
    if VOICE_OK:
        st.success("🎤 Voice I/O available")
    else:
        st.warning(
            "🎤 Voice unavailable\n\n"
            "Install:\n`pip install faster-whisper sounddevice scipy edge-tts`"
        )
    st.caption(f"Model: {GROQ_MODEL} (Groq)")

# ── Chat initialisation ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hey! 💪 I'm FitBot, your AI fitness coach.\n\n"
                "I can see your recent fitness data — workouts, diet logs, sleep, and body stats — "
                "so I can give you **personalized advice** rather than generic tips.\n\n"
                "Ask me anything, or tap a quick question on the left!"
            ),
        }
    ]

# ── Render existing messages ───────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Voice UI ───────────────────────────────────────────────────────────────────
if VOICE_OK:
    st.markdown("""
    <style>
    .voice-box {
        background: linear-gradient(135deg, #0f172a, #111827);
        border-radius: 20px;
        padding: 18px 20px;
        border: 1px solid #334155;
        box-shadow: 0 0 20px rgba(0,255,255,0.12);
        margin-bottom: 16px;
    }
    .glow-label {
        color: #67e8f9;
        font-size: 15px;
        text-align: center;
        letter-spacing: 0.5px;
    }
    .wave { display:flex; justify-content:center; gap:4px; margin:10px 0 14px; }
    .wave span {
        width:5px; height:22px; background:cyan;
        border-radius:8px; animation:wave 1s infinite ease-in-out;
    }
    .wave span:nth-child(2){animation-delay:.15s}
    .wave span:nth-child(3){animation-delay:.3s}
    .wave span:nth-child(4){animation-delay:.45s}
    .wave span:nth-child(5){animation-delay:.6s}
    @keyframes wave{0%,100%{transform:scaleY(.5)}50%{transform:scaleY(1.8)}}
    </style>
    <div class="voice-box">
      <p class="glow-label">🎙️ AI Voice Assistant Ready</p>
      <div class="wave">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Optional Lottie animation
    mic_anim = load_lottie("https://assets2.lottiefiles.com/packages/lf20_eq9hnyqv.json")
    if mic_anim:
        try:
            from streamlit_lottie import st_lottie # pyright: ignore[reportMissingImports]
            st_lottie(mic_anim, height=120, key="mic_anim")
        except ImportError:
            pass

    voice_cols = st.columns([1, 1])
    with voice_cols[0]:
        start_voice = st.button(
            "🎤 Speak to FitBot",
            use_container_width=True,
            type="primary",
        )
    with voice_cols[1]:
        voice_tts = st.toggle("🔊 Speak replies aloud", value=True, key="tts_toggle")

    # ── Voice processing — runs ONCE per button click ─────────────────────────
    if start_voice:
        status = st.status("🎧 Listening… speak now!", expanded=True)
        with status:
            st.write("Recording — stops automatically when you pause…")
            from utils.voice_ai import listen
            user_voice = listen(max_seconds=8)
            status.update(label="✅ Transcribed! Thinking…", state="running")

        if user_voice.strip():
            with st.chat_message("user"):
                st.markdown(f"🎤 *{user_voice}*")
            st.session_state.messages.append({"role": "user", "content": user_voice})

            client = get_groq_client()
            if client:
                with st.chat_message("assistant"):
                    reply_placeholder = st.empty()
                    full_reply = ""

                    # Stream the voice response (shorter = faster TTS)
                    stream = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=(
                            [{"role": "system", "content": SYSTEM_PROMPT}]
                            + [{"role": m["role"], "content": m["content"]}
                               for m in st.session_state.messages]
                        ),
                        max_tokens=600,
                        stream=True,
                    )
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content or ""
                        full_reply += delta
                        reply_placeholder.markdown(full_reply + "▌")

                    reply_placeholder.markdown(full_reply)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": full_reply}
                    )

                    # Speak the reply
                    if voice_tts and full_reply:
                        from utils.voice_ai import autoplay_audio
                        audio_html = autoplay_audio(full_reply)
                        if audio_html:
                            st.markdown(audio_html, unsafe_allow_html=True)

            status.update(label="✅ Done!", state="complete")
        else:
            status.update(label="⚠️ Nothing heard — please try again", state="error")

        st.rerun()   # scroll to bottom after new messages

# ── Text input ─────────────────────────────────────────────────────────────────
# Drain pending quick-question before reading chat_input
pending = st.session_state.pop("pending_prompt", None)
prompt = st.chat_input("Ask your fitness coach anything…") or pending

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = get_groq_client()
    if not client:
        with st.chat_message("assistant"):
            st.error("GROQ_API_KEY not found in .env file.")
        st.stop()

    with st.chat_message("assistant"):
        reply_placeholder = st.empty()
        full_reply = ""

        try:
            # ── STREAMING: text appears word-by-word, no waiting ──────────────
            stream = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=(
                    [{"role": "system", "content": SYSTEM_PROMPT}]
                    + [{"role": m["role"], "content": m["content"]}
                       for m in st.session_state.messages]
                ),
                max_tokens=1200,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_reply += delta
                reply_placeholder.markdown(full_reply + "▌")   # live typing cursor

            reply_placeholder.markdown(full_reply)             # clean final render

        except Exception as e:
            full_reply = f"API Error: {e}"
            reply_placeholder.error(full_reply)

        st.session_state.messages.append({"role": "assistant", "content": full_reply})

        # Optional TTS for typed chat (only if toggle is on)
        if VOICE_OK and st.session_state.get("tts_toggle", False) and full_reply:
            try:
                from utils.voice_ai import autoplay_audio
                audio_html = autoplay_audio(full_reply)
                if audio_html:
                    st.markdown(audio_html, unsafe_allow_html=True)
            except Exception:
                pass    # TTS failure should never crash the chat
