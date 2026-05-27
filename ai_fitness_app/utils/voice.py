from gtts import gTTS # pyright: ignore[reportMissingImports]
import tempfile
import base64

def autoplay_audio(text):

    tts = gTTS(text=text, lang="en")

    fp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    tts.save(fp.name)

    with open(fp.name, "rb") as f:

        audio_bytes = f.read()

    b64 = base64.b64encode(audio_bytes).decode()

    md = f"""
    <audio autoplay>
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """

    return md