from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List, Optional
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.db.models import Task


def create_task(db: Session, task: TaskCreate, user_id: int) -> Task:
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
    return db_task


def get_task(db: Session, task_id: int, user_id: int) -> Optional[Task]:
    return (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        .first()
    )


def get_tasks(
    db: Session,
    user_id: int,
    parent_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Task]:
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
    db: Session, task_id: int, user_id: int, task_update: TaskUpdate
) -> Optional[Task]:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return None

    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(
    db: Session, task_id: int, user_id: int, soft_delete: bool = True
) -> bool:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return False

    if soft_delete:
        from datetime import datetime

        db_task.deleted_at = datetime.utcnow()
        db.commit()
    else:
        db.delete(db_task)
        db.commit()
    return True


def get_task_breadcrumb(db: Session, task_id: int, user_id: int):
    """Get the breadcrumb path for a task using the custom function"""
    result = db.execute(
        text("SELECT * FROM get_task_breadcrumb(:task_id)"), {"task_id": task_id}
    )
    breadcrumb = [
        {"id": row.id, "title": row.title, "level": row.level} for row in result
    ]

    # Verify user has access to this task
    if (
        breadcrumb
        and db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
        is None
    ):
        return []

    return breadcrumb


def get_task_children(db: Session, task_id: int, user_id: int):
    """Get all children of a task using the custom function"""
    # First verify user has access to this task
    if not get_task(db, task_id, user_id):
        return []

    result = db.execute(
        text("SELECT * FROM get_task_children(:task_id)"), {"task_id": task_id}
    )
    return [{"id": row.id, "title": row.title, "level": row.level} for row in result]
