from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import ConfigDict, EmailStr
from sqlmodel import TIMESTAMP, Column, Field, Relationship, SQLModel, text
from sqlalchemy.dialects.postgresql import JSONB


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=120, unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')))
    trips: list["Trip"] = Relationship(back_populates="owner")

class Trip(SQLModel, table=True):
    __tablename__ = "trips"

    id: Optional[int] = Field(default=None, primary_key=True)
    destination: str = Field(max_length=50)
    days: int = Field(gt=0)
    budget: int = Field(gt=0)
    trip_style: str = Field(max_length=100)
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", ondelete="CASCADE")
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')))
    owner: Optional[User] = Relationship(back_populates="trips")
    itinerary: Optional["Itinerary"] = Relationship(back_populates="trip")

class Itinerary(SQLModel, table=True):
    __tablename__ = "itineraries"

    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: Optional[int] = Field(default=None, foreign_key="trips.id", unique=True, ondelete="CASCADE")
    days: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')))
    trip: Optional[Trip] = Relationship(back_populates="itinerary")

class UserBase(SQLModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr
class UserCreate(UserBase):
    password: str = Field(min_length=8)
class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: Optional[datetime] = None



