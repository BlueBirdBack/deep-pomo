from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from pydantic import ConfigDict


class PomodoroBase(BaseModel):
    start_time: Optional[datetime] = None
    duration: int  # Planned duration in seconds
    session_type: str = Field(..., pattern="^(work|short_break|long_break)$")


class PomodoroCreate(PomodoroBase):
    pass


class PomodoroUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    actual_duration: Optional[int] = None
    session_type: Optional[str] = Field(None, pattern="^(work|short_break|long_break)$")
    completed: Optional[bool] = None
    interruption_reason: Optional[str] = None


class PomodoroSession(PomodoroBase):
    id: int
    user_id: int
    end_time: Optional[datetime] = None
    actual_duration: Optional[int] = None
    completed: bool
    interruption_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PomodoroTaskAssociationBase(BaseModel):
    pomodoro_session_id: int
    task_id: int
    time_spent: Optional[int] = None
    notes: Optional[str] = None


class PomodoroTaskAssociationCreate(PomodoroTaskAssociationBase):
    pass


class PomodoroTaskAssociation(PomodoroTaskAssociationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
