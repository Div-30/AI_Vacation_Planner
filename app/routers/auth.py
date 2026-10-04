from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.database import get_db
from app import models
from app.services import user_service, auth_service
from app.utils import create_access_token

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: models.UserCreate, db: Session = Depends(get_db)):
    existing_username = user_service.get_user_by_username(db, user.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    existing_email = user_service.get_user_by_email(db, user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return user_service.create_user(db, user)



@router.post("/login", response_model=models.TokenResponse)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials"
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return models.TokenResponse(access_token=access_token, token_type="bearer")