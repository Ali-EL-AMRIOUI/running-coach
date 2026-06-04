from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db import models
from schemas.user import UserProfile, UserResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.put("/profile")
def update_profile(
    profile: UserProfile,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    for key, value in profile.dict(exclude_unset=True).items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully", "profile": profile.dict()}
