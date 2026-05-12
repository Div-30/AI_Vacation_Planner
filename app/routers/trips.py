from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import models
from app.database import get_db


router = APIRouter(
    prefix="/api/trips",
    tags=["Trips"]
)

@router.get("/", response_model=list[models.TripResponse])
def get_all_trips(owner_id: int, db: Session = Depends(get_db))

