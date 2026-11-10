"""
voice.py - Speech to text with Whisper on Groq (free). Works for English, Urdu and mixed speech.

The browser records a short clip (webm / ogg / mp4 / wav), we send it to Whisper and get text back.
The text then goes to the agent like a typed message. The audio is never saved.
Text to speech (the agent talking back) happens in the browser itself - free and offline.
"""
import logging

from fastapi import HTTPException

from app import config

log = logging.getLogger("voice")
AUDIO_TYPES = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/mpeg": "mp3",
               "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac", "audio/m4a": "m4a"}


def transcribe(audio: bytes, content_type: str, language: str = None) -> str:
    if not config.GROQ_API_KEY:
        raise HTTPException(503, "Voice needs a GROQ_API_KEY in backend/.env. Please type your message.")
    extension = AUDIO_TYPES.get((content_type or "").split(";")[0].strip())
    if not extension:
        raise HTTPException(415, "Unsupported audio format.")
    from groq import Groq
    try:
        result = Groq(api_key=config.GROQ_API_KEY, timeout=30).audio.transcriptions.create(
            file=(f"voice.{extension}", audio), model=config.WHISPER_MODEL,
            language=language if language in ("en", "ur") else None,
            prompt="Solar panels, inverter, battery, units, bill, load-shedding, kW, IESCO, LESCO.",
            temperature=0)
    except Exception:
        log.exception("Whisper failed")
        raise HTTPException(502, "Could not understand the recording. Please try again or type.")
    text = (getattr(result, "text", "") or "").strip()
    if not text:
        raise HTTPException(422, "I could not hear anything. Please speak a little closer to the microphone.")
    return text[:config.MAX_MESSAGE_CHARS]
