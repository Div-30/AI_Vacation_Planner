from sqlmodel import Session, select

from app import models
from app.utils import hash_password


def get_user_by_id(db:Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)

def get_user_by_email(db: Session, email: str) -> models.User | None:
    statement = select(models.User).where(models.User.email == email)
    return db.exec(statement).first()

def get_user_by_username(db: Session, username: str) -> models.User | None:
    statement = select(models.User).where(models.User.username == username)
    return db.exec(statement).first()

def create_user(db: Session, user: models.UserCreate) -> models.User:
    hashed = hash_password(user.password)
    new_user = models.User(username= user.username, email=user.email, hashed_password=hashed)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
