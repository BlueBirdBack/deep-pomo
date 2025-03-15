"""Test task completion functionality"""

from datetime import datetime, timezone
from fastapi import status
import pytest


@pytest.mark.tasks
def test_task_completed_at_timestamp(authorized_client):
    """Test that completed_at timestamp is set when task status changes to completed"""
    # Create a task in pending status
    task_data = {"title": "Complete me", "status": "pending"}
    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == status.HTTP_201_CREATED
    task_id = response.json()["id"]

    # Get the task and verify completed_at is None
    task_response = authorized_client.get(f"/api/v1/tasks/{task_id}")
    assert task_response.json()["completed_at"] is None

    # Update to completed status
    update_data = {"status": "completed"}
    before_update = datetime.now(timezone.utc)
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify completed_at was set automatically by the trigger
    task_response = authorized_client.get(f"/api/v1/tasks/{task_id}")
    completed_at = datetime.fromisoformat(task_response.json()["completed_at"])

    # Allow a small buffer for database processing time
    # Rather than exact bounds checking, ensure it's within a reasonable time window
    time_diff = abs((completed_at - before_update).total_seconds())
    assert (
        time_diff < 10
    ), f"Completion timestamp is too far from update time: {time_diff} seconds"

    # Change back to in_progress
    update_data = {"status": "in_progress"}
    response = authorized_client.patch(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify completed_at is now None again
    task_response = authorized_client.get(f"/api/v1/tasks/{task_id}")
    assert task_response.json()["completed_at"] is None
