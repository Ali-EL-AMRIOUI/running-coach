"""
db/models.py
SQLAlchemy Models - Running Coach SaaS
"""

from sqlalchemy import (
    Column, Integer, String, Float,
    DateTime, JSON, Boolean, Text, ForeignKey
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String, unique=True, index=True, nullable=False)
    hashed_password     = Column(String, nullable=False)

    # Profile
    age                 = Column(Integer, nullable=True)
    weight              = Column(Float, nullable=True)
    height              = Column(Float, nullable=True)
    gender              = Column(String, nullable=True)

    # Level
    level               = Column(String, default="beginner")
    weekly_volume       = Column(Float, default=20.0)
    current_frequency   = Column(Integer, default=4)

    # Records (in seconds)
    best_400m           = Column(Integer, nullable=True)
    best_800m           = Column(Integer, nullable=True)
    best_1500m          = Column(Integer, nullable=True)
    best_5k             = Column(Integer, nullable=True)
    best_10k            = Column(Integer, nullable=True)
    best_half           = Column(Integer, nullable=True)
    best_marathon       = Column(Integer, nullable=True)

    # Goal
    goal_distance       = Column(String, nullable=True)
    goal_date           = Column(DateTime, nullable=True)

    # Preferences
    training_days       = Column(Integer, default=4)
    double_session      = Column(String, default="no")

    # Subscription
    subscription_status = Column(String, default="free")
    subscription_end    = Column(DateTime, nullable=True)
    stripe_customer_id  = Column(String, nullable=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    plans               = relationship("TrainingPlan", back_populates="user")
    workout_logs        = relationship("WorkoutLog", back_populates="user")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # Goal
    distance        = Column(String, nullable=False)
    goal_date       = Column(DateTime, nullable=True)
    weeks_count     = Column(Integer, default=12)

    # Generated plan
    plan            = Column(JSON, nullable=False)
    total_volume    = Column(Float, default=0.0)
    coach_analysis  = Column(Text, nullable=True)

    # Calculated pace zones (saved for reference)
    pace_zones      = Column(JSON, nullable=True)

    # Meta
    level           = Column(String, nullable=True)
    is_valid        = Column(Boolean, default=True)
    validation_errors = Column(JSON, nullable=True)

    # Athlete feedback
    user_rating     = Column(Integer, nullable=True)
    user_feedback   = Column(Text, nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user            = relationship("User", back_populates="plans")
    workout_logs    = relationship("WorkoutLog", back_populates="plan")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    plan_id          = Column(Integer, ForeignKey("training_plans.id"), index=True, nullable=True)

    # Session
    date             = Column(DateTime, server_default=func.now())
    workout_type     = Column(String)
    distance         = Column(Float)
    duration         = Column(Integer)  # in seconds
    avg_pace         = Column(String, nullable=True)  # e.g., "4:30/km"
    avg_hr           = Column(Integer, nullable=True)
    perceived_effort = Column(Integer, nullable=True)  # 1-10
    notes            = Column(Text, nullable=True)
    completed        = Column(Boolean, default=True)

    # Strava
    strava_activity_id = Column(String, nullable=True)

    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user             = relationship("User", back_populates="workout_logs")
    plan             = relationship("TrainingPlan", back_populates="workout_logs")


class AppFeedback(Base):
    __tablename__ = "app_feedback"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    category    = Column(String, nullable=False)   # bug, feature_request, general
    message     = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
