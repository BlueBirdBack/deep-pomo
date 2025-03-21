"""Pomodoro session routes"""

from typing import List, Optional
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.auth import get_current_user
from app.schemas.pomodoros import (
    PomodoroSession,
    PomodoroCreate,
    PomodoroUpdate,
    PomodoroTaskAssociation,
    PomodoroTaskAssociationCreate,
)
from app.db.repositories import pomodoros as pomodoros_repository
from app.db.repositories import tasks as tasks_repository
from app.schemas.users import User
from app.db.repositories import users as users_repository

router = APIRouter(prefix="/pomodoros", tags=["pomodoros"])


@router.post("/", response_model=PomodoroSession, status_code=status.HTTP_201_CREATED)
def create_pomodoro(
    pomodoro: PomodoroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new pomodoro session"""
    return pomodoros_repository.create_pomodoro(db, pomodoro, current_user.id)


@router.get("/", response_model=List[PomodoroSession])
def read_pomodoros(
    completed: Optional[bool] = None,
    session_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pomodoro sessions"""
    return pomodoros_repository.get_pomodoros(
        db,
        user_id=current_user.id,
        completed=completed,
        session_type=session_type,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/{pomodoro_id}", response_model=PomodoroSession)
def read_pomodoro(
    pomodoro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific pomodoro session"""
    pomodoro = pomodoros_repository.get_pomodoro(db, pomodoro_id, current_user.id)
    if not pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )
    return pomodoro


@router.patch("/{pomodoro_id}", response_model=PomodoroSession)
def update_pomodoro(
    pomodoro_id: int,
    pomodoro_update: PomodoroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a pomodoro session, including interruption details"""
    return pomodoros_repository.update_pomodoro(
        db, pomodoro_id, current_user.id, pomodoro_update
    )


@router.post("/{pomodoro_id}/complete", response_model=PomodoroSession)
def complete_pomodoro(
    pomodoro_id: int,
    end_time: Optional[datetime] = None,
    actual_duration: Optional[int] = None,
    interruption_reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a pomodoro session"""
    completed_pomodoro = pomodoros_repository.complete_pomodoro(
        db,
        pomodoro_id,
        current_user.id,
        end_time=end_time,
        actual_duration=actual_duration,
        interruption_reason=interruption_reason,
    )
    if not completed_pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )
    return completed_pomodoro


@router.delete("/{pomodoro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pomodoro(
    pomodoro_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a pomodoro session"""
    success = pomodoros_repository.delete_pomodoro(
        db, pomodoro_id, current_user.id, soft_delete=not permanent
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )
    return {"detail": "Pomodoro session deleted successfully"}


@router.post("/{pomodoro_id}/tasks", response_model=PomodoroTaskAssociation)
def associate_task_with_pomodoro(
    pomodoro_id: int,
    association: PomodoroTaskAssociationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Associate a task with a pomodoro session"""
    # Ensure the provided pomodoro_id matches the one in the association data
    if association.pomodoro_session_id != pomodoro_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pomodoro ID in path must match the one in request body",
        )

    result = pomodoros_repository.associate_task_with_pomodoro(
        db, association, current_user.id
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pomodoro session or task not found",
        )

    return result


@router.get("/{pomodoro_id}/tasks", response_model=List[PomodoroTaskAssociation])
def get_pomodoro_tasks(
    pomodoro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all tasks associated with a pomodoro session"""
    # Verify pomodoro exists and belongs to user
    pomodoro = pomodoros_repository.get_pomodoro(db, pomodoro_id, current_user.id)
    if not pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )

    return pomodoros_repository.get_tasks_for_pomodoro(db, pomodoro_id, current_user.id)


@router.get("/task/{task_id}", response_model=List[PomodoroSession])
def get_task_pomodoros(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pomodoro sessions associated with a task"""
    # Verify task exists and belongs to user
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return pomodoros_repository.get_pomodoros_for_task(db, task_id, current_user.id)


@router.post("/{pomodoro_id}/pause", response_model=PomodoroSession)
def pause_pomodoro(
    pomodoro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause a pomodoro session"""
    result = pomodoros_repository.pause_pomodoro(db, pomodoro_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pomodoro session not found or already completed",
        )
    return result


@router.post("/{pomodoro_id}/resume", response_model=PomodoroSession)
def resume_pomodoro(
    pomodoro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused pomodoro session"""
    result = pomodoros_repository.resume_pomodoro(db, pomodoro_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pomodoro session not found or already completed",
        )
    return result


@router.get("/{pomodoro_id}/pause-stats", response_model=dict)
def get_pomodoro_pause_stats(
    pomodoro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pause statistics for a pomodoro session"""
    # Verify pomodoro exists and belongs to user
    pomodoro = pomodoros_repository.get_pomodoro(db, pomodoro_id, current_user.id)
    if not pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )

    return pomodoros_repository.get_pomodoro_pause_stats(db, pomodoro_id)


@router.post(
    "/preset", response_model=PomodoroSession, status_code=status.HTTP_201_CREATED
)
def create_preset_pomodoro(
    session_type: str = Query(..., pattern="^(work|short_break|long_break)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new pomodoro session with preset duration based on type and user settings"""
    # Get user settings for durations
    user_settings = users_repository.get_user_settings(db, current_user.id)
    if not user_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User settings not found"
        )

    # Map session type to the appropriate duration from user settings
    duration_map = {
        "work": user_settings.pomodoro_duration,
        "short_break": user_settings.short_break_duration,
        "long_break": user_settings.long_break_duration,
    }

    pomodoro = PomodoroCreate(
        start_time=datetime.now(UTC),
        duration=duration_map[session_type],  # type: ignore
        session_type=session_type,
    )

    return pomodoros_repository.create_pomodoro(db, pomodoro, current_user.id)
