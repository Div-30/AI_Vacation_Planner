import base64
import os
import tempfile

import pyttsx3
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app import models
from app.config import settings

ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav", "audio/wave", "audio/x-wave",
    "audio/mpeg", "audio/mp3",
    "audio/ogg", "audio/webm", 
}

MAX_AUDIO_BYTES = 15 * 1024 * 1024

EXTRACTION_PROMPT = """Listen to this audio of someone describing a trip they want to take.
Extract the following trip details:
- destination: the city or place name they mention.
- days: number of days for the trip. If not stated, default to 5.
- budget: total trip budget as a plain integer. If not stated, default to 1500.
- trip_style: a short phrase for the style (e.g. 'relaxed', 'adventure', 'foodie',
  'family'). If not stated, default to 'balanced sightseeing'.
"""

def transcribe_and_extract_trip(audio_bytes: bytes, mime_type: str) -> models.TripCreate:
    if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise ValueError(f"Unsupported audio format: {mime_type}")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Audio file is too large; please send a shorter clip.")
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    message = HumanMessage(content=[
        {"type": "text", "text": EXTRACTION_PROMPT},
        {"type": "media", "data": encoded_audio, "mime_type": mime_type}
    ])

    llm = ChatGoogleGenerativeAI(
        model=settings.voice_llm_model,
        api_key=settings.google_api_key
    ).with_structured_output(models.TripCreate)
    return llm.invoke([message])

def itinerary_to_speech_text(destination: str, days: list[dict]) -> str:
    lines = [f"Here is your {len(days)}-day itinerary for {destination}."]
    for day in days:
        lines.append(f"Day {day['day_number']}: {day['theme_or_focus']}.")
        for activity in day["activities"]:
            lines.append(f"At {activity['time']}, {activity['description']} at {activity['location']}.")
    return " ".join(lines)

def synthesize_speech(text: str) -> bytes:
    engine = pyttsx3.init()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    try:
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.remove(tmp_path)
