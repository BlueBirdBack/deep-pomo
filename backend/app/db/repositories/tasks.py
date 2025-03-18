"""Task repository"""

from typing import List, Optional
from datetime import datetime, UTC
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.schemas.tasks import TaskCreate
from app.db.models import Task, TaskHistory


def create_task(db: Session, task: TaskCreate, user_id: int) -> Task:
    """Create a task"""
    db_task = Task(
        user_id=user_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        parent_id=task.parent_id,
        color_code=task.color_code,
        estimated_duration=task.estimated_duration,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Create history entry for task creation
    history_entry = TaskHistory(
        task_id=db_task.id,
        user_id=user_id,
        action="created",
        changes={
            "title": {"old": None, "new": task.title},
            "description": {"old": None, "new": task.description},
            "priority": {"old": None, "new": task.priority},
            "status": {"old": None, "new": task.status},
            "parent_id": {"old": None, "new": task.parent_id},
            "color_code": {"old": None, "new": task.color_code},
            "estimated_duration": {"old": None, "new": task.estimated_duration},
        },
    )
    db.add(history_entry)
    db.commit()

    return db_task


def get_task(
    db: Session, task_id: int, user_id: int, include_deleted: bool = False
) -> Optional[Task]:
    """Get a task by ID"""
    query = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id)

    if not include_deleted:
        query = query.filter(Task.deleted_at.is_(None))

    return query.first()


def get_tasks(
    db: Session,
    user_id: int,
    parent_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Task]:
    """Get all tasks"""
    query = db.query(Task).filter(Task.user_id == user_id, Task.deleted_at.is_(None))

    if parent_id is not None:
        query = query.filter(Task.parent_id == parent_id)
    else:
        # Root tasks (no parent)
        query = query.filter(Task.parent_id.is_(None))

    if status:
        query = query.filter(Task.status == status)

    return query.offset(skip).limit(limit).all()


def update_task(
    db: Session, task_id: int, user_id: int, task_update: dict
) -> Optional[Task]:
    """Update a task with the given fields"""
    # First get the task to ensure it exists and belongs to the user
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return None

    # Record old values for history
    changes = {}

    # Update task fields
    for key, new_value in task_update.items():
        old_value = getattr(db_task, key)
        if old_value != new_value:  # Only record if value actually changed
            changes[key] = {"old": old_value, "new": new_value}
            setattr(db_task, key, new_value)

    # Handle completed_at field based on status changes
    if "status" in changes:
        # If status changed to completed, set completed_at
        if changes["status"]["new"] == "completed" and db_task.completed_at is None:
            completed_at = datetime.now(UTC)
            db_task.completed_at = completed_at
            changes["completed_at"] = {
                "old": None,
                "new": completed_at.isoformat() if completed_at else None,
            }
            # Ensure the change is committed to the database immediately
            db.flush()

        # If status changed from completed to something else, reset completed_at
        elif (
            changes["status"]["old"] == "completed"
            and changes["status"]["new"] != "completed"
        ):
            changes["completed_at"] = {
                "old": (
                    db_task.completed_at.isoformat() if db_task.completed_at else None
                ),
                "new": None,
            }
            db_task.completed_at = None  # type: ignore
            # Ensure the change is committed to the database immediately
            db.flush()

    # Only create history entry if there were actual changes
    if changes:
        history_entry = TaskHistory(
            task_id=task_id,
            user_id=user_id,
            action="updated",
            changes=changes,
        )
        db.add(history_entry)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(
    db: Session, task_id: int, user_id: int, soft_delete: bool = True
) -> bool:
    """Delete a task"""
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return False

    if soft_delete:
        # Record old value for history
        old_deleted_at = db_task.deleted_at
        new_deleted_at = datetime.now(UTC)

        # Update the task
        db_task.deleted_at = new_deleted_at  # type: ignore

        # Create history entry
        history_entry = TaskHistory(
            task_id=task_id,
            user_id=user_id,
            action="soft_deleted",
            changes={
                "deleted_at": {
                    "old": old_deleted_at.isoformat() if old_deleted_at else None,
                    "new": new_deleted_at.isoformat(),
                }
            },
        )
        db.add(history_entry)
        db.commit()
    else:
        # For hard delete, we don't create history since the task will be gone
        db.delete(db_task)
        db.commit()

    return True


def get_task_breadcrumb(db: Session, task_id: int, user_id: int):
    """Get the breadcrumb for a task"""
    # Verify task exists and belongs to user
    task = get_task(db, task_id, user_id)
    if not task:
        return []

    # Call the PostgreSQL function through SQLAlchemy
    return (
        db.query(Task.id, Task.title, (func.nlevel(Task.path) - 1).label("level"))
        .filter(
            text(f"path @> (SELECT path FROM tasks WHERE id = {task_id})"),
            Task.deleted_at.is_(None),
        )
        .order_by(Task.path)
        .all()
    )


def get_task_children(db: Session, task_id: int, user_id: int):
    """Get all children of a task using the custom function"""
    # First verify user has access to this task
    if not get_task(db, task_id, user_id):
        return []

    result = db.execute(
        text("SELECT * FROM get_task_children(:task_id)"), {"task_id": task_id}
    )
    return [{"id": row.id, "title": row.title, "level": row.level} for row in result]


def get_task_history(db: Session, task_id: int):
    """Get history for a specific task"""
    return (
        db.query(TaskHistory)
        .filter(TaskHistory.task_id == task_id)
        .order_by(TaskHistory.timestamp.asc())
        .all()
    )


def restore_task(db: Session, task_id: int, user_id: int):
    """Restore a soft-deleted task"""
    db_task = get_task(db, task_id, user_id, include_deleted=True)
    if not db_task:
        return None

    # Record the old value for history
    old_deleted_at = db_task.deleted_at

    # Restore the task
    db_task.deleted_at = None  # type: ignore
    db.commit()
    db.refresh(db_task)

    # Create history entry
    history_entry = TaskHistory(
        task_id=task_id,
        user_id=user_id,
        action="restored",
        changes={
            "deleted_at": {
                "old": old_deleted_at.isoformat() if old_deleted_at else None,
                "new": None,
            }
        },
    )
    db.add(history_entry)
    db.commit()

    return db_task
