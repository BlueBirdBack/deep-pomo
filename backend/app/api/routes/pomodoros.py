from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
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

router = APIRouter(prefix="/pomodoros", tags=["pomodoros"])


@router.post("/", response_model=PomodoroSession, status_code=status.HTTP_201_CREATED)
def create_pomodoro(
    pomodoro: PomodoroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    pomodoro = pomodoros_repository.get_pomodoro(db, pomodoro_id, current_user.id)
    if not pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )
    return pomodoro


@router.put("/{pomodoro_id}", response_model=PomodoroSession)
def update_pomodoro(
    pomodoro_id: int,
    pomodoro_update: PomodoroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_pomodoro = pomodoros_repository.update_pomodoro(
        db, pomodoro_id, current_user.id, pomodoro_update
    )
    if not updated_pomodoro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pomodoro session not found"
        )
    return updated_pomodoro


@router.post("/{pomodoro_id}/complete", response_model=PomodoroSession)
def complete_pomodoro(
    pomodoro_id: int,
    end_time: Optional[datetime] = None,
    actual_duration: Optional[int] = None,
    interruption_reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    # Verify task exists and belongs to user
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return pomodoros_repository.get_pomodoros_for_task(db, task_id, current_user.id)
