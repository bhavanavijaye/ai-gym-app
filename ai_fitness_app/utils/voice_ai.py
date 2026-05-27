"""
voice_ai.py  —  Optimized voice I/O for the AI Fitness Coach
Key fixes vs original:
  • WhisperModel is cached — loads ONCE per session, not on every call
  • Silence-detection recording: stops after 1.5s of quiet (not fixed 5s)
  • edge_tts async runs in a dedicated event loop to avoid asyncio conflicts
  • Temp files always cleaned up, even on error
  • gTTS fallback if edge_tts is unavailable
"""

import tempfile
import base64
import os
import threading
import time
import numpy as np # pyright: ignore[reportMissingImports]

# ── Lazy / cached model ────────────────────────────────────────────────────────
_whisper_model = None
_model_lock = threading.Lock()

def _get_model():
    """Load WhisperModel once and cache it for the lifetime of the process."""
    global _whisper_model
    if _whisper_model is None:
        with _model_lock:
            if _whisper_model is None:          # double-checked locking
                from faster_whisper import WhisperModel # pyright: ignore[reportMissingImports]
                _whisper_model = WhisperModel(
                    "base",
                    compute_type="int8",
                    num_workers=1,              # don't spawn extra threads
                )
    return _whisper_model


# ── Audio recording with silence detection ─────────────────────────────────────
def record_audio(
    max_seconds: int = 8,
    silence_threshold: float = 0.02,   # RMS below this → silence
    silence_duration: float = 1.2,     # seconds of silence to stop early
    sample_rate: int = 16_000,         # 16kHz — matches Whisper's native rate
) -> str:
    """
    Record from the microphone.
    Stops automatically after `silence_duration` seconds of quiet,
    or when `max_seconds` is reached — whichever comes first.
    Returns the path to a temp WAV file (caller must delete it).
    """
    import sounddevice as sd # pyright: ignore[reportMissingImports]
    from scipy.io.wavfile import write as wav_write # pyright: ignore[reportMissingImports]

    chunk = int(sample_rate * 0.1)          # 100 ms chunks
    max_chunks = int(max_seconds / 0.1)
    silence_chunks_needed = int(silence_duration / 0.1)

    frames = []
    silence_count = 0
    speech_started = False

    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32")
    stream.start()

    for _ in range(max_chunks):
        data, _ = stream.read(chunk)
        frames.append(data.copy())
        rms = float(np.sqrt(np.mean(data ** 2)))

        if rms > silence_threshold:
            speech_started = True
            silence_count = 0
        elif speech_started:
            silence_count += 1
            if silence_count >= silence_chunks_needed:
                break           # natural end of speech detected

    stream.stop()
    stream.close()

    audio = np.concatenate(frames, axis=0)

    # Convert to int16 for WAV
    audio_int16 = (audio * 32767).astype(np.int16)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wav_write(tmp.name, sample_rate, audio_int16)
    return tmp.name


# ── Speech → Text ──────────────────────────────────────────────────────────────
def listen(max_seconds: int = 8) -> str:
    """
    Record the user's voice and return the transcribed text.
    Returns an empty string if nothing was said or transcription failed.
    """
    audio_path = None
    try:
        audio_path = record_audio(max_seconds=max_seconds)
        model = _get_model()
        segments, info = model.transcribe(
            audio_path,
            beam_size=1,            # beam_size=1 is ~3× faster than default 5
            language="en",          # skip language detection, saves ~200ms
            condition_on_previous_text=False,
            vad_filter=True,        # skip silent regions automatically
            vad_parameters=dict(
                min_silence_duration_ms=400,
                threshold=0.4,
            ),
        )
        return "".join(s.text for s in segments).strip()
    except Exception as e:
        print(f"[voice_ai] listen() error: {e}")
        return ""
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ── Text → Speech ──────────────────────────────────────────────────────────────
def _tts_edge(text: str, output_path: str) -> bool:
    """
    Generate speech with edge_tts (high quality, Microsoft neural voices).
    Returns True on success, False on failure.
    Runs the async function in a fresh event loop to avoid conflicts with
    Streamlit's own event loop.
    """
    try:
        import edge_tts, asyncio # pyright: ignore[reportMissingImports]

        async def _run():
            communicate = edge_tts.Communicate(text, voice="en-US-JennyNeural")
            await communicate.save(output_path)

        # Use a dedicated new event loop — never asyncio.run() inside Streamlit
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
        return True
    except Exception as e:
        print(f"[voice_ai] edge_tts failed: {e}")
        return False


def _tts_gtts(text: str, output_path: str) -> bool:
    """Fallback: gTTS (needs internet, slightly robotic but reliable)."""
    try:
        from gtts import gTTS # pyright: ignore[reportMissingImports]
        gTTS(text=text, lang="en").save(output_path)
        return True
    except Exception as e:
        print(f"[voice_ai] gTTS fallback failed: {e}")
        return False


def autoplay_audio(text: str) -> str:
    """
    Convert `text` to speech and return an HTML <audio autoplay> snippet.
    Tries edge_tts first, then falls back to gTTS.
    Returns an empty string if both fail.
    """
    # Trim very long responses so TTS stays snappy
    if len(text) > 600:
        # Speak only the first ~3 sentences
        sentences = text.replace("\n", " ").split(". ")
        text = ". ".join(sentences[:3]).strip() + "."

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()

    try:
        ok = _tts_edge(text, tmp.name) or _tts_gtts(text, tmp.name)
        if not ok or os.path.getsize(tmp.name) == 0:
            return ""

        with open(tmp.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        return (
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
            f"</audio>"
        )
    except Exception as e:
        print(f"[voice_ai] autoplay_audio error: {e}")
        return ""
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)