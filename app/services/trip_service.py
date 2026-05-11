from sqlmodel import Session, select

from app import models


def get_all_trips(db: Session, owner_id: int) -> list[models.Trip]:
    statement = select(models.Trip).where(models.Trip.owner_id == owner_id)
    return db.exec(statement).all()

def get_trip_by_id(db: Session, owner_id: int) -> models.Trip | None:
    statement = db.get(models.Trip, owner_id)
    return db.exec(statement).first()

def create_trip(db: Session, trip: models.TripCreate, owner_id: int) -> models.Trip | None:
    new_trip = models.Trip(**trip.model_dump(), owner_id=owner_id)
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    return new_trip

def update_trip(db: Session, trip_id: int, owner_id: int, updated_trip: models.TripUpdate):
    trip = get_trip_by_id(db, trip_id= trip_id, owner_id=owner_id)
    if not trip:
        return None
    updated_data = updated_trip.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(trip, key, value)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip

def delete_trip(db: Session, trip_id: int, owner_id: int):
    trip = get_trip_by_id(db, trip_id= trip_id, owner_id=owner_id)
    if not trip:
        return False
    db.delete(trip)
    db.commit()
    return True


