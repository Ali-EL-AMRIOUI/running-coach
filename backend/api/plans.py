"""
api/plans.py
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import Optional
from fastapi.responses import JSONResponse

from db.database import get_db
from db import crud
from schemas.plan import PlanRequest, TrainingPlanSchema
from core.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router   = APIRouter(prefix="/plans", tags=["Training Plans"])
security = HTTPBearer(auto_error=False)


def get_current_user_id(credentials, db) -> int:
    # TODO: décoder JWT
    return 1


@router.post("/generate")
def generate_plan(
    request: PlanRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SQLAlchemySession = Depends(get_db),
):
    user_id = get_current_user_id(credentials, db)
    try:
        orchestrator = AgentOrchestrator(db=db, user_id=user_id)
        plan_data    = orchestrator.run_workflow(request)

        # Sauvegarde DB
        saved = crud.save_plan(
            db        = db,
            user_id   = user_id,
            plan_data = plan_data,
            distance  = request.goal_distance,
            goal_date = request.goal_date,
        )

        # Retourner le plan + l'ID pour le frontend
        return {
            "id":             saved.id,
            "coach_analysis": plan_data.get("coach_analysis", ""),
            "total_km":       plan_data.get("total_km", 0),
            "weeks":          plan_data.get("weeks", []),
        }

    except Exception as e:
        logger.error(f"❌ Erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_all_plans(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SQLAlchemySession = Depends(get_db),
):
    user_id = get_current_user_id(credentials, db)
    plans   = crud.get_user_plans(db, user_id)
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SQLAlchemySession = Depends(get_db),
):
    user_id = get_current_user_id(credentials, db)
    plan    = crud.get_plan(db, plan_id, user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé")

    plan_json = plan.plan if isinstance(plan.plan, dict) else {}
    return {
        "id":             plan.id,
        "distance":       plan.distance,
        "weeks_count":    plan.weeks_count,
        "total_km":       plan.total_volume,
        "coach_analysis": plan_json.get("coach_analysis", plan.coach_analysis or ""),
        "total_km":       plan_json.get("total_km", plan.total_volume),
        "weeks":          plan_json.get("weeks", []),
        "created_at":     plan.created_at.isoformat() if plan.created_at else None,
    }


@router.post("/{plan_id}/feedback")
def submit_feedback(
    plan_id: int,
    rating: int,
    feedback: str = "",
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SQLAlchemySession = Depends(get_db),
):
    user_id = get_current_user_id(credentials, db)
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating entre 1 et 5")
    plan = crud.update_plan_feedback(db, plan_id, user_id, rating, feedback)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    return {"message": "Feedback enregistré", "plan_id": plan_id}


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SQLAlchemySession = Depends(get_db),
):
    user_id = get_current_user_id(credentials, db)
    deleted = crud.delete_plan(db, plan_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan non trouvé")
    return {"message": "Plan supprimé"}