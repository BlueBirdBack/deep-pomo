import pytest
from fastapi import status
from datetime import datetime
from app.db.models import Task


def test_task_completion(authorized_client, test_user, db):
    """Test that completed_at is set when task status changes to completed"""
    # Create a task
    task_data = {"title": "Test Task", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Initial state - completed_at should be None
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task.completed_at is None

    # Update task to completed
    update_data = {"status": "completed"}
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify completed_at was automatically set
    db.refresh(task)
    assert task.completed_at is not None

    # Change back to pending
    update_data = {"status": "pending"}
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify completed_at was reset to None
    db.refresh(task)
    assert task.completed_at is None
