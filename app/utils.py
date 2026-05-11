from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from app import models
from app.config import settings
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def verify_access_token(token: str, credentials_exception) -> models.TokenData:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithm=[settings.algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return models.TokenData(id=int(user_id))
    except JWTError:
        raise credentials_exception