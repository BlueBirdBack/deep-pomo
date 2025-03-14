from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.schemas.pomodoros import (
    PomodoroCreate,
    PomodoroUpdate,
    PomodoroTaskAssociationCreate,
)
from app.db.models import PomodoroSession, PomodoroTaskAssociation


def create_pomodoro(
    db: Session, pomodoro: PomodoroCreate, user_id: int
) -> PomodoroSession:
    db_pomodoro = PomodoroSession(
        user_id=user_id,
        start_time=pomodoro.start_time or datetime.utcnow(),
        duration=pomodoro.duration,
        session_type=pomodoro.session_type,
    )
    db.add(db_pomodoro)
    db.commit()
    db.refresh(db_pomodoro)
    return db_pomodoro


def get_pomodoro(
    db: Session, pomodoro_id: int, user_id: int
) -> Optional[PomodoroSession]:
    return (
        db.query(PomodoroSession)
        .filter(
            PomodoroSession.id == pomodoro_id,
            PomodoroSession.user_id == user_id,
            PomodoroSession.deleted_at.is_(None),
        )
        .first()
    )


def get_pomodoros(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    completed: Optional[bool] = None,
    session_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[PomodoroSession]:
    query = db.query(PomodoroSession).filter(
        PomodoroSession.user_id == user_id, PomodoroSession.deleted_at.is_(None)
    )

    if completed is not None:
        query = query.filter(PomodoroSession.completed == completed)

    if session_type:
        query = query.filter(PomodoroSession.session_type == session_type)

    if start_date:
        query = query.filter(PomodoroSession.start_time >= start_date)

    if end_date:
        query = query.filter(PomodoroSession.start_time <= end_date)

    return (
        query.order_by(PomodoroSession.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_pomodoro(
    db: Session, pomodoro_id: int, user_id: int, pomodoro_update: PomodoroUpdate
) -> Optional[PomodoroSession]:
    db_pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not db_pomodoro:
        return None

    update_data = pomodoro_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pomodoro, key, value)

    db.commit()
    db.refresh(db_pomodoro)
    return db_pomodoro


def complete_pomodoro(
    db: Session,
    pomodoro_id: int,
    user_id: int,
    end_time: Optional[datetime] = None,
    actual_duration: Optional[int] = None,
    interruption_reason: Optional[str] = None,
) -> Optional[PomodoroSession]:
    db_pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not db_pomodoro:
        return None

    db_pomodoro.completed = True
    db_pomodoro.end_time = end_time or datetime.utcnow()

    if actual_duration is not None:
        db_pomodoro.actual_duration = actual_duration
    else:
        # Calculate actual duration in seconds
        delta = db_pomodoro.end_time - db_pomodoro.start_time
        db_pomodoro.actual_duration = int(delta.total_seconds())

    if interruption_reason:
        db_pomodoro.interruption_reason = interruption_reason

    db.commit()
    db.refresh(db_pomodoro)
    return db_pomodoro


def delete_pomodoro(
    db: Session, pomodoro_id: int, user_id: int, soft_delete: bool = True
) -> bool:
    db_pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not db_pomodoro:
        return False

    if soft_delete:
        db_pomodoro.deleted_at = datetime.utcnow()
        db.commit()
    else:
        db.delete(db_pomodoro)
        db.commit()
    return True


def associate_task_with_pomodoro(
    db: Session, association: PomodoroTaskAssociationCreate
) -> PomodoroTaskAssociation:
    db_association = PomodoroTaskAssociation(
        pomodoro_session_id=association.pomodoro_session_id,
        task_id=association.task_id,
        time_spent=association.time_spent,
        notes=association.notes,
    )
    db.add(db_association)
    db.commit()
    db.refresh(db_association)
    return db_association


def get_tasks_for_pomodoro(db: Session, pomodoro_id: int, user_id: int):
    """Get all tasks associated with a pomodoro session"""
    # First verify user has access to this pomodoro
    if not get_pomodoro(db, pomodoro_id, user_id):
        return []

    return (
        db.query(PomodoroTaskAssociation)
        .filter(
            PomodoroTaskAssociation.pomodoro_session_id == pomodoro_id,
            PomodoroTaskAssociation.deleted_at.is_(None),
        )
        .all()
    )


def get_pomodoros_for_task(db: Session, task_id: int, user_id: int):
    """Get all pomodoro sessions associated with a task"""
    from app.db.models import Task

    # First verify user has access to this task
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        .first()
    )

    if not task:
        return []

    associations = (
        db.query(PomodoroTaskAssociation)
        .filter(
            PomodoroTaskAssociation.task_id == task_id,
            PomodoroTaskAssociation.deleted_at.is_(None),
        )
        .all()
    )

    pomodoro_ids = [assoc.pomodoro_session_id for assoc in associations]

    return (
        db.query(PomodoroSession)
        .filter(
            PomodoroSession.id.in_(pomodoro_ids), PomodoroSession.deleted_at.is_(None)
        )
        .all()
    )
