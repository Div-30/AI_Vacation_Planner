from fastapi import APIRouter, Depends
from app import models
from app.oauth2 import get_current_user

router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)

@router.get("/me", response_model=models.UserResponse)
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    
    return current_user