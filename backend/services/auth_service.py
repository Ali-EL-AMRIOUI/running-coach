"""
services/auth_service.py
Business logic for user registration and login.
Routers call into this module; they should not talk to the DB directly.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from db import models
from utils.auth import get_password_hash, verify_password, create_access_token


def register_user(db: Session, email: str, password: str) -> models.User:
    """
    Creates a new user with a hashed password.
    Raises HTTPException(400) if the email is already registered.
    """
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(password)
    new_user = models.User(
        email=email,
        hashed_password=hashed_password,
        subscription_status="free",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> models.User:
    """
    Verifies credentials and returns the matching user.
    Raises HTTPException(401) if the email is unknown or the password is wrong.
    """
    db_user = db.query(models.User).filter(models.User.email == email).first()

    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return db_user


def build_token_for_user(user: models.User) -> str:
    """Issues a JWT access token for an already-authenticated user."""
    return create_access_token(data={"sub": str(user.id)})
