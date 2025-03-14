from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.core.auth import get_current_user
from app.schemas.tasks import (
    Task,
    TaskCreate,
    TaskUpdate,
    TaskBreadcrumb,
    TaskWithChildren,
)
from app.db.repositories import tasks as tasks_repository
from app.schemas.users import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # If parent_id is provided, verify it exists and belongs to the user
    if task.parent_id:
        parent_task = tasks_repository.get_task(db, task.parent_id, current_user.id)
        if not parent_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent task not found"
            )

    return tasks_repository.create_task(db, task, current_user.id)


@router.get("/", response_model=List[Task])
def read_tasks(
    parent_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return tasks_repository.get_tasks(
        db,
        user_id=current_user.id,
        parent_id=parent_id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{task_id}", response_model=Task)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.put("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # If parent_id is being updated, verify it exists and belongs to the user
    if task_update.parent_id is not None:
        # Check for circular reference
        if task_update.parent_id == task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task cannot be its own parent",
            )

        if task_update.parent_id != 0:  # 0 means set to null/root
            parent_task = tasks_repository.get_task(
                db, task_update.parent_id, current_user.id
            )
            if not parent_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent task not found",
                )
        else:
            # Convert 0 to None for setting as root task
            task_update.parent_id = None

    updated_task = tasks_repository.update_task(
        db, task_id, current_user.id, task_update
    )
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = tasks_repository.delete_task(
        db, task_id, current_user.id, soft_delete=not permanent
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return {"detail": "Task deleted successfully"}


@router.get("/{task_id}/breadcrumb", response_model=List[TaskBreadcrumb])
def get_task_breadcrumb(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return tasks_repository.get_task_breadcrumb(db, task_id, current_user.id)


@router.get("/{task_id}/children", response_model=List[TaskBreadcrumb])
def get_task_children(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return tasks_repository.get_task_children(db, task_id, current_user.id)


@router.get("/{task_id}/tree", response_model=TaskWithChildren)
def get_task_with_children(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a task with all its children in a hierarchical structure"""
    task = tasks_repository.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Get all children
    children = tasks_repository.get_task_children(db, task_id, current_user.id)

    # Convert task to TaskWithChildren model
    task_dict = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "parent_id": task.parent_id,
        "color_code": task.color_code,
        "estimated_duration": task.estimated_duration,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "children": [],
    }

    # Build hierarchical structure
    # This is a simplified approach - for a real app, you might want a more efficient algorithm
    for child in children:
        if child["level"] == 1:  # Direct children
            task_dict["children"].append(
                {"id": child["id"], "title": child["title"], "children": []}
            )

    return task_dict
