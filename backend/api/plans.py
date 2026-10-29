"""
api/plans.py
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from db.database import get_db
from db import crud, models
from schemas.plan import PlanRequest, TrainingPlanSchema
from core.agents.orchestrator import AgentOrchestrator
from utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plans", tags=["Training Plans"])


@router.post("/generate")
def generate_plan(
    request: PlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    try:
        orchestrator = AgentOrchestrator(db=db, user_id=current_user.id)
        plan_data    = orchestrator.run_workflow(request)

        # Save to DB
        saved = crud.save_plan(
            db        = db,
            user_id   = current_user.id,
            plan_data = plan_data,
            distance  = request.goal_distance,
            goal_date = request.goal_date,
        )

        # Return the plan + its ID for the frontend
        return {
            "id":             saved.id,
            "coach_analysis": plan_data.get("coach_analysis", ""),
            "total_km":       plan_data.get("total_km", 0),
            "weeks":          plan_data.get("weeks", []),
        }

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_all_plans(
    current_user: models.User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    plans = crud.get_user_plans(db, current_user.id)
    return [
        {
            "id":           p.id,
            "distance":     p.distance,
            "weeks":        p.weeks_count,
            "total_km":     p.total_volume,
            "created_at":   p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/{plan_id}")
def get_plan(
    plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    plan = crud.get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_json = plan.plan if isinstance(plan.plan, dict) else {}
    return {
        "id":             plan.id,
        "distance":       plan.distance,
        "weeks_count":    plan.weeks_count,
        "total_km":       plan_json.get("total_km", plan.total_volume),
        "coach_analysis": plan_json.get("coach_analysis", plan.coach_analysis or ""),
        "weeks":          plan_json.get("weeks", []),
        "created_at":     plan.created_at.isoformat() if plan.created_at else None,
    }


@router.post("/{plan_id}/feedback")
def submit_feedback(
    plan_id: int,
    rating: int,
    feedback: str = "",
    current_user: models.User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    plan = crud.update_plan_feedback(db, plan_id, current_user.id, rating, feedback)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Feedback recorded", "plan_id": plan_id}


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    deleted = crud.delete_plan(db, plan_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted"}