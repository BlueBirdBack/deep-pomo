import pytest
from fastapi import status
from app.db.models import Task, PomodoroSession, PomodoroTaskAssociation


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
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task is not None
    assert task.deleted_at is not None


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
        task = db.query(Task).filter(Task.id == task_id).first()
        assert task.deleted_at is not None

    # No tasks should be returned in the tasks list
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 0
