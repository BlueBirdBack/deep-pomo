"""Test soft deleting tasks and restoring them"""

import pytest
from fastapi import status
from app.db.models import Task


@pytest.mark.tasks
def test_task_soft_delete(authorized_client, test_user, db):
    """Test soft deleting a task"""
    # Create a task
    task_data = {"title": "Test Task", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Soft delete the task
    response = authorized_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Task should not be returned in normal queries
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 0

    # But it should still exist in the database with deleted_at set
    task = (
        db.query(Task).filter(Task.id == task_id, Task.user_id == test_user.id).first()
    )
    assert task is not None
    assert task.deleted_at is not None


@pytest.mark.tasks
def test_hierarchical_soft_delete_cascade(authorized_client, test_user, db):
    """Test soft deleting a parent task cascades to all children"""
    # Create a parent task
    parent_task_data = {"title": "Parent Task", "status": "pending"}
    parent_response = authorized_client.post("/api/v1/tasks/", json=parent_task_data)
    parent_id = parent_response.json()["id"]

    # Create children tasks
    child_ids = []
    for i in range(3):
        child_task_data = {
            "title": f"Child {i}",
            "status": "pending",
            "parent_id": parent_id,
        }
        child_response = authorized_client.post("/api/v1/tasks/", json=child_task_data)
        child_ids.append(child_response.json()["id"])

    # Create a grandchild
    grandchild_data = {
        "title": "Grandchild",
        "status": "pending",
        "parent_id": child_ids[0],
    }
    grandchild_response = authorized_client.post("/api/v1/tasks/", json=grandchild_data)
    grandchild_id = grandchild_response.json()["id"]

    # Soft delete the parent task
    response = authorized_client.delete(f"/api/v1/tasks/{parent_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # All children and grandchildren should be soft deleted
    for task_id in child_ids + [grandchild_id]:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == test_user.id)
            .first()
        )
        assert task.deleted_at is not None

    # No tasks should be returned in the tasks list
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 0


@pytest.mark.tasks
def test_task_restoration(authorized_client, test_user, db):
    """Test restoring a soft-deleted task"""
    # Create a task
    task_data = {"title": "Task to Restore", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Soft delete the task
    response = authorized_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify task is soft deleted
    task = (
        db.query(Task).filter(Task.id == task_id, Task.user_id == test_user.id).first()
    )
    assert task.deleted_at is not None

    # Restore the task (by setting deleted_at to None)
    task.deleted_at = None
    db.commit()

    # Task should now appear in normal queries
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id


@pytest.mark.tasks
def test_hierarchical_restoration_cascade(authorized_client, test_user, db):
    """Test restoring a parent task cascades to all children"""
    # Create a parent task
    parent_task_data = {"title": "Parent Task", "status": "pending"}
    parent_response = authorized_client.post("/api/v1/tasks/", json=parent_task_data)
    parent_id = parent_response.json()["id"]

    # Create children tasks
    child_ids = []
    for i in range(3):
        child_task_data = {
            "title": f"Child {i}",
            "status": "pending",
            "parent_id": parent_id,
        }
        child_response = authorized_client.post("/api/v1/tasks/", json=child_task_data)
        child_ids.append(child_response.json()["id"])

    # Create a grandchild
    grandchild_data = {
        "title": "Grandchild",
        "status": "pending",
        "parent_id": child_ids[0],
    }
    grandchild_response = authorized_client.post("/api/v1/tasks/", json=grandchild_data)
    grandchild_id = grandchild_response.json()["id"]

    # Soft delete the parent task
    response = authorized_client.delete(f"/api/v1/tasks/{parent_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify all tasks are soft deleted
    for task_id in [parent_id] + child_ids + [grandchild_id]:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == test_user.id)
            .first()
        )
        assert task.deleted_at is not None

    # Restore the parent task
    parent_task = (
        db.query(Task)
        .filter(Task.id == parent_id, Task.user_id == test_user.id)
        .first()
    )
    parent_task.deleted_at = None
    db.commit()

    # Manually restore all children and grandchildren
    for task_id in child_ids + [grandchild_id]:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == test_user.id)
            .first()
        )
        task.deleted_at = None
    db.commit()

    # All children and grandchildren should be restored
    for task_id in child_ids + [grandchild_id]:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == test_user.id)
            .first()
        )
        assert task.deleted_at is None

    # Root task should appear in the tasks list
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 1  # Only the parent task (root task)
    assert tasks[0]["id"] == parent_id

    # Check that children are returned when querying with parent_id
    response = authorized_client.get(f"/api/v1/tasks/?parent_id={parent_id}")
    assert response.status_code == status.HTTP_200_OK
    child_tasks = response.json()
    assert len(child_tasks) == 3  # All 3 children

    # Check that grandchild is returned when querying with its parent_id
    response = authorized_client.get(f"/api/v1/tasks/?parent_id={child_ids[0]}")
    assert response.status_code == status.HTTP_200_OK
    grandchild_tasks = response.json()
    assert len(grandchild_tasks) == 1  # The grandchild
    assert grandchild_tasks[0]["id"] == grandchild_id

    # Alternatively, verify all tasks exist in the database
    all_tasks = (
        db.query(Task)
        .filter(Task.user_id == test_user.id, Task.deleted_at.is_(None))
        .all()
    )
    assert len(all_tasks) == 5  # Parent + 3 children + 1 grandchild
