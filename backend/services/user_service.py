"""
services/user_service.py
Business logic for reading and updating a user's profile.
"""

from sqlalchemy.orm import Session

from db import models


def update_user_profile(db: Session, user: models.User, profile_data: dict) -> models.User:
    """
    Applies the given fields to the user and persists the change.
    Only fields explicitly provided (exclude_unset) are touched.
    """
    for key, value in profile_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user
