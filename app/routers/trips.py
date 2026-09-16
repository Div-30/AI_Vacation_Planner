from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app import models
from app.database import get_db
from app.oauth2 import get_current_user
from app.services import trip_service


router = APIRouter(
    prefix="/api/trips",
    tags=["Trips"]
)

@router.get("/", response_model=list[models.TripResponse])
def get_all_trips(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return trip_service.get_all_trips(db, current_user.id)
@router.post("/", response_model=models.TripCreateResponse, status_code=status.HTTP_201_CREATED)
def create_trip(trip: models.TripCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_trip = trip_service.create_trip(db, trip, current_user.id)
    return {**new_trip.model_dump(), "message": "Trip created successfully"}
@router.get("/{id}", response_model=models.TripResponse)
def get_trip_by_id(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trip = trip_service.get_trip_by_id(db, trip_id = id, owner_id = current_user.id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The trip with id {id} not found")
    return trip
@router.put("/{id}", response_model=models.TripUpdate)
def update_trip(id: int, updated_trip: models.TripUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trip = trip_service.update_trip(db, trip_id= id, owner_id=current_user.id, updated_trip= updated_trip)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The trip with id {id} not found")
    return trip
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trip = trip_service.delete_trip(db, trip_id=id, owner_id=current_user.id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The trip with id {id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
    
