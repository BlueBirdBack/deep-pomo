from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, UTC
from app.schemas.pomodoros import (
    PomodoroCreate,
    PomodoroUpdate,
    PomodoroTaskAssociationCreate,
)
from app.db.models import (
    PomodoroSession,
    PomodoroTaskAssociation,
    PomodoroSessionInterruption,
)
from sqlalchemy.sql import text


def create_pomodoro(
    db: Session, pomodoro: PomodoroCreate, user_id: int
) -> PomodoroSession:
    db_pomodoro = PomodoroSession(
        user_id=user_id,
        start_time=pomodoro.start_time or datetime.now(UTC),
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
    """Update a pomodoro session with new values"""
    db_pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not db_pomodoro:
        return None

    # Update the pomodoro with the provided values
    update_data = pomodoro_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pomodoro, key, value)

    # If completing or interrupting, ensure end_time and actual_duration are set
    if "completed" in update_data or "interruption_reason" in update_data:
        if not db_pomodoro.end_time:
            db_pomodoro.end_time = datetime.now(UTC)

        if not db_pomodoro.actual_duration:
            # Ensure both datetimes are timezone-aware
            start_time = db_pomodoro.start_time
            end_time = db_pomodoro.end_time

            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)

            db_pomodoro.actual_duration = int((end_time - start_time).total_seconds())

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
    db_pomodoro.end_time = end_time or datetime.now(UTC)

    if actual_duration is not None:
        db_pomodoro.actual_duration = actual_duration
    else:
        # Ensure both datetimes are timezone-aware before subtraction
        start_time = db_pomodoro.start_time
        end_time = db_pomodoro.end_time

        # Convert naive datetime to aware if needed
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=UTC)

        # Calculate actual duration in seconds
        delta = end_time - start_time
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
        db_pomodoro.deleted_at = datetime.now(UTC)
        db.commit()
    else:
        db.delete(db_pomodoro)
        db.commit()
    return True


def associate_task_with_pomodoro(
    db: Session, association: PomodoroTaskAssociationCreate, user_id: int
) -> Optional[PomodoroTaskAssociation]:
    # Verify both pomodoro and task exist and belong to user
    from app.db.models import Task

    pomodoro = get_pomodoro(db, association.pomodoro_session_id, user_id)
    task = (
        db.query(Task)
        .filter(
            Task.id == association.task_id,
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
        )
        .first()
    )

    if not pomodoro or not task:
        return None

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


def pause_pomodoro(
    db: Session, pomodoro_id: int, user_id: int
) -> Optional[PomodoroSession]:
    """Pause a pomodoro session by creating an interruption record"""
    pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not pomodoro:
        return None

    if pomodoro.completed:
        return None

    # Check if there's already an active pause
    pause_stats = db.execute(
        text("SELECT * FROM get_session_pause_stats(:session_id)"),
        {"session_id": pomodoro_id},
    ).fetchone()

    if pause_stats and pause_stats.is_paused:
        # Already paused, nothing to do
        return pomodoro

    # Create a new interruption record
    interruption = PomodoroSessionInterruption(
        pomodoro_session_id=pomodoro_id, paused_at=datetime.now(UTC)
    )
    db.add(interruption)
    db.commit()
    db.refresh(pomodoro)

    return pomodoro


def resume_pomodoro(
    db: Session, pomodoro_id: int, user_id: int
) -> Optional[PomodoroSession]:
    """Resume a paused pomodoro session"""
    pomodoro = get_pomodoro(db, pomodoro_id, user_id)
    if not pomodoro:
        return None

    if pomodoro.completed:
        return None

    # Check if there's an active pause
    pause_stats = db.execute(
        text("SELECT * FROM get_session_pause_stats(:session_id)"),
        {"session_id": pomodoro_id},
    ).fetchone()

    if not pause_stats or not pause_stats.is_paused:
        # Not paused, nothing to do
        return pomodoro

    # Get the current pause record
    interruption = (
        db.query(PomodoroSessionInterruption)
        .filter(PomodoroSessionInterruption.id == pause_stats.current_pause_id)
        .first()
    )

    if interruption:
        now = datetime.now(UTC)
        interruption.resumed_at = now
        # Calculate pause duration
        interruption.duration = int((now - interruption.paused_at).total_seconds())
        db.commit()
        db.refresh(pomodoro)

    return pomodoro


def get_pomodoro_pause_stats(db: Session, pomodoro_id: int) -> dict:
    """Get pause statistics for a pomodoro session"""
    stats = db.execute(
        text("SELECT * FROM get_session_pause_stats(:session_id)"),
        {"session_id": pomodoro_id},
    ).fetchone()

    if not stats:
        return {"is_paused": False, "current_pause_id": None, "total_pause_duration": 0}

    return {
        "is_paused": stats.is_paused,
        "current_pause_id": stats.current_pause_id,
        "total_pause_duration": stats.total_pause_duration,
    }
