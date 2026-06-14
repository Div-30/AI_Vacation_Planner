from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import models
from app.database import get_db
from app.oauth2 import get_current_user
from app.services import itinerary_service, trip_service, llm_service


router = APIRouter(prefix="/api/itineraries", tags=["Itineraries"])

@router.post("/", response_model=models.ItineraryCreateResponse, status_code=status.HTTP_201_CREATED)
def create_itinerary(request: models.ItineraryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trip = trip_service.get_trip_by_id(db, trip_id = itinerary.trip_id, owner_id = current_user.id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The trip with id {itinerary.trip_id} not found Or unauthorized")
    new_itinerary = itinerary_service.create_itinerary(db, itinerary)
    return {**new_itinerary.model_dump(), "message": "Itinerary created successfully"}
@router.get("/{trip_id}", response_model=models.ItineraryResponse)
def get_itinerary_by_trip_id(trip_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trip = trip_service.get_trip_by_id(db, trip_id = trip_id, owner_id = current_user.id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The trip with id {trip_id} not found Or unauthorized")
    itinerary = itinerary_service.get_itinerary_by_trip_id(db, trip_id=trip_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No itinerary found for trip id {trip_id}")
    return itinerary