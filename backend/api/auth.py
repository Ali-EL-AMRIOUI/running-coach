from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from db import models
from schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from utils.auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Vérifier si l'utilisateur existe
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        subscription_status="free"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Créer token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            level=new_user.level,
            subscription_status=new_user.subscription_status,
            created_at=new_user.created_at
        )
    )

@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Chercher l'utilisateur
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    
    # Vérifier existence
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Vérifier mot de passe
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Créer token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            level=db_user.level,
            subscription_status=db_user.subscription_status,
            created_at=db_user.created_at
        )
    )
