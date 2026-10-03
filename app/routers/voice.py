from fastapi import APIRouter, Depends, HTTPException, UploadFile, Response, status
from sqlmodel import Session

from app import models
from app.database import get_db
from app.oauth2 import get_current_user
from app.services import trip_service, voice_service, itinerary_service


router = APIRouter(prefix="/api/voice", tags=["Voice"])

@router.post("/trips", response_model=models.TripCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_trip_from_voice(
    audio: UploadFile,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    try:
        trip_in = voice_service.transcribe_and_extract_trip(audio_bytes, audio.content_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    new_trip = trip_service.create_trip(db, trip_in, current_user.id)
    return {**new_trip.model_dump(), "message": "Trip create from voice input"}

@router.get("/itineraries/{trip_id}/audio")
def get_itinerary_audio(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trip = trip_service.get_trip_by_id(db, trip_id=trip_id, owner_id=current_user.id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No itinerary found for trip id {trip_id}")
    itinerary = itinerary_service.get_itinerary_by_trip_id(db, trip_id=trip_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No itinerary found for trip id {trip_id}")
    speech_text = voice_service.itinerary_to_speech_text(trip.destination, itinerary.days)
    audio_bytes = voice_service.synthesize_speech(speech_text)

    return Response(content=audio_bytes, media_type="audio/wav")