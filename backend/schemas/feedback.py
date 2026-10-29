from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class FeedbackCreate(BaseModel):
    category: str = Field(..., pattern="^(bug|feature_request|general)$")
    message: str = Field(..., min_length=1, max_length=2000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    message: str
    created_at: datetime
