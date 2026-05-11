from sqlmodel import Session, select

from app import models


def get_itinerary_by_trip_id(db: Session, trip_id: int) -> models.Itinerary | None:
    statement = select(models.Itinerary).where(models.Itinerary.trip_id == trip_id)
    return db.exec(statement).first()

def create_itinerary(db: Session, itinerary = models.ItineraryCreate) -> models.Itinerary:
    new_itinerary = models.Itinerary(**itinerary.model_dump())
    db.add(new_itinerary)
    db.commit()
    db.refresh(new_itinerary)
    
    return new_itinerary
