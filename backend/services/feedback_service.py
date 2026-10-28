"""
services/feedback_service.py
Business logic for submitting and listing app feedback.
"""

from sqlalchemy.orm import Session
from typing import Optional

from db import models


def create_feedback(
    db: Session,
    user_id: Optional[int],
    category: str,
    message: str,
) -> models.AppFeedback:
    feedback = models.AppFeedback(
        user_id=user_id,
        category=category,
        message=message,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_user_feedback(db: Session, user_id: int, limit: int = 50) -> list[models.AppFeedback]:
    return (
        db.query(models.AppFeedback)
        .filter(models.AppFeedback.user_id == user_id)
        .order_by(models.AppFeedback.created_at.desc())
        .limit(limit)
        .all()
    )
