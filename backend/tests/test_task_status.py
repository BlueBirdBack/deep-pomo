"""Test task status transitions and history"""

import pytest
from fastapi import status
from app.db.models import Task


@pytest.mark.tasks
def test_task_completion(
    authorized_client, test_user, db
):  # pylint: disable=unused-argument
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


@pytest.mark.tasks
def test_task_status_transitions(
    authorized_client, test_user, db
):  # pylint: disable=unused-argument
    """Test all valid task status transitions"""
    # Create a task
    task_data = {"title": "Status Transition Task", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Test all valid status transitions
    status_sequence = ["in_progress", "blocked", "in_progress", "completed", "pending"]

    for new_status in status_sequence:
        update_data = {"status": new_status}
        response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify status was updated
        data = response.json()
        assert data["status"] == new_status

        # Check completed_at field when transitioning to/from completed
        task = db.query(Task).filter(Task.id == task_id).first()
        db.refresh(task)
        if new_status == "completed":
            assert task.completed_at is not None
        else:
            assert task.completed_at is None


@pytest.mark.tasks
def test_task_history_on_status_change(
    authorized_client, test_user
):  # pylint: disable=unused-argument
    """Test that task history is recorded when status changes"""
    # Create a task
    task_data = {"title": "History Status Task", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Change status
    update_data = {"status": "completed"}
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Get task history
    response = authorized_client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()

    # Should have two history entries (create + status update)
    assert len(history) == 2
    assert history[0]["action"] == "created"
    assert history[1]["action"] == "updated"

    # Check that status change was recorded in history
    changes = history[1]["changes"]
    assert "status" in changes
    assert changes["status"]["old"] == "pending"
    assert changes["status"]["new"] == "completed"

    # Also verify completed_at was recorded
    assert "completed_at" in changes
    assert changes["completed_at"]["old"] is None
    assert changes["completed_at"]["new"] is not None
