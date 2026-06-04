from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from db.database import get_db
from db import models
from schemas.workout import WorkoutCreate, WorkoutResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/workouts", tags=["Workouts"])

@router.post("/log", response_model=WorkoutResponse)
def log_workout(
    workout: WorkoutCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_workout = models.WorkoutLog(
        user_id=current_user.id,
        plan_id=workout.plan_id,
        workout_type=workout.workout_type,
        distance=workout.distance,
        duration=workout.duration,
        avg_hr=workout.avg_hr,
        perceived_effort=workout.perceived_effort,
        notes=workout.notes,
        completed=workout.completed
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    
    return WorkoutResponse.from_orm(new_workout)

@router.get("/", response_model=List[WorkoutResponse])
def get_workouts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    workouts = db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id
    ).order_by(models.WorkoutLog.date.desc()).limit(limit).all()
    
    return workouts

@router.get("/stats")
def get_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workouts = db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id
    ).all()
    
    total_distance = sum(w.distance or 0 for w in workouts)
    total_duration = sum(w.duration or 0 for w in workouts)
    total_workouts = len(workouts)
    
    return {
        "total_workouts": total_workouts,
        "total_distance_km": round(total_distance, 1),
        "total_hours": round(total_duration / 60, 1)
    }
