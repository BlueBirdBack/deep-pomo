from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    status: Optional[str] = Field(
        "pending", pattern="^(pending|in_progress|completed|blocked)$"
    )
    parent_id: Optional[int] = None
    color_code: Optional[str] = None
    estimated_duration: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    status: Optional[str] = Field(
        None, pattern="^(pending|in_progress|completed|blocked)$"
    )
    parent_id: Optional[int] = None
    color_code: Optional[str] = None
    estimated_duration: Optional[int] = None


class Task(TaskBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TaskBreadcrumb(BaseModel):
    id: int
    title: str
    level: int


class TaskChild(BaseModel):
    id: int
    title: str
    children: List["TaskChild"] = []


class TaskWithChildren(Task):
    children: List[TaskChild] = []


# Resolve forward references
TaskChild.update_forward_refs()
