"""Test task history endpoints"""

import pytest
from fastapi import status


@pytest.mark.task_history
def test_task_history_create(authorized_client, test_user, db):
    """Test task history is created when a task is created"""

    task_data = {"title": "Test Task", "status": "pending", "priority": "high"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == status.HTTP_201_CREATED
    task_id = response.json()["id"]

    # Get task history
    response = authorized_client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()

    # Should have one history entry for task creation
    assert len(history) == 1
    assert history[0]["action"] == "created"
    assert history[0]["user_id"] == test_user.id
    assert history[0]["task_id"] == task_id


@pytest.mark.task_history
def test_task_history_update(authorized_client):
    """Test task history is created when a task is updated"""

    # Create a task
    task_data = {"title": "Original Title", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Update the task
    update_data = {
        "title": "Updated Title",
        "status": "in_progress",
        "priority": "high",
    }
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Get task history
    response = authorized_client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()

    # Should have two history entries (create + update)
    assert len(history) == 2
    assert history[0]["action"] == "created"
    assert history[1]["action"] == "updated"

    # Check changes were recorded
    changes = history[1]["changes"]
    assert "title" in changes
    assert changes["title"]["old"] == "Original Title"
    assert changes["title"]["new"] == "Updated Title"
    assert changes["status"]["old"] == "pending"
    assert changes["status"]["new"] == "in_progress"


@pytest.mark.task_history
def test_task_history_soft_delete(authorized_client):
    """Test task history is created when a task is soft deleted"""
    # Create a task
    task_data = {"title": "Task to Delete", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Soft delete the task
    response = authorized_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Get task history
    response = authorized_client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()

    # Should have two history entries (create + soft_delete)
    assert len(history) == 2
    assert history[0]["action"] == "created"
    assert history[1]["action"] == "soft_deleted"

    # Check changes were recorded
    changes = history[1]["changes"]
    assert "deleted_at" in changes
    assert changes["deleted_at"]["old"] is None
    assert changes["deleted_at"]["new"] is not None


@pytest.mark.task_history
def test_task_history_restore(authorized_client):
    """Test task history is created when a soft-deleted task is restored"""
    # Create a task
    task_data = {"title": "Task to Restore", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Soft delete the task
    response = authorized_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Restore the task (assuming you have an endpoint for this)
    response = authorized_client.post(f"/api/v1/tasks/{task_id}/restore")
    assert response.status_code == status.HTTP_200_OK

    # Get task history
    response = authorized_client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()

    # Should have three history entries (create + soft_delete + restore)
    assert len(history) == 3
    assert history[0]["action"] == "created"
    assert history[1]["action"] == "soft_deleted"
    assert history[2]["action"] == "restored"

    # Check changes were recorded
    changes = history[2]["changes"]
    assert "deleted_at" in changes
    assert changes["deleted_at"]["old"] is not None
    assert changes["deleted_at"]["new"] is None
