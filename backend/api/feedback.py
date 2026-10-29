from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db import models
from schemas.feedback import FeedbackCreate, FeedbackResponse
from utils.auth import get_current_user
from services import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(
    feedback: FeedbackCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    created = feedback_service.create_feedback(
        db, current_user.id, feedback.category, feedback.message
    )
    return created


@router.get("/", response_model=List[FeedbackResponse])
def list_my_feedback(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return feedback_service.get_user_feedback(db, current_user.id)
