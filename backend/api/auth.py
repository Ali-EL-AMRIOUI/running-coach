from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    new_user = auth_service.register_user(db, user.email, user.password)
    access_token = auth_service.build_token_for_user(new_user)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            level=new_user.level,
            subscription_status=new_user.subscription_status,
            created_at=new_user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = auth_service.authenticate_user(db, user.email, user.password)
    access_token = auth_service.build_token_for_user(db_user)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            level=db_user.level,
            subscription_status=db_user.subscription_status,
            created_at=db_user.created_at,
        ),
    )
