from sqlmodel import Session

from app import models
from app.services import user_service
from app.utils import verify_password


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    user = user_service.get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
    