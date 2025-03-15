"""Test retrieving breadcrumb navigation for a task"""

import pytest
from fastapi import status


@pytest.mark.tasks
def test_get_task_breadcrumb(authorized_client, test_user, db):
    """Test retrieving breadcrumb navigation for a task"""
    # Create a hierarchy: Task A -> Task B -> Task C
    task_a_data = {"title": "Task A", "status": "pending"}
    task_a_response = authorized_client.post("/api/v1/tasks/", json=task_a_data)
    task_a_id = task_a_response.json()["id"]

    task_b_data = {"title": "Task B", "status": "pending", "parent_id": task_a_id}
    task_b_response = authorized_client.post("/api/v1/tasks/", json=task_b_data)
    task_b_id = task_b_response.json()["id"]

    task_c_data = {"title": "Task C", "status": "pending", "parent_id": task_b_id}
    task_c_response = authorized_client.post("/api/v1/tasks/", json=task_c_data)
    task_c_id = task_c_response.json()["id"]

    # Verify tasks were created with correct user_id
    from app.db.models import Task

    tasks = db.query(Task).filter(Task.user_id == test_user.id).all()
    assert len(tasks) == 3

    # Verify task hierarchy in database
    task_c = db.query(Task).filter(Task.id == task_c_id).first()
    assert task_c.user_id == test_user.id
    assert task_c.parent_id == task_b_id

    # Get breadcrumb for Task C
    response = authorized_client.get(f"/api/v1/tasks/{task_c_id}/breadcrumb")
    assert response.status_code == status.HTTP_200_OK

    breadcrumb = response.json()

    # Verify breadcrumb contains all three tasks in correct order
    assert len(breadcrumb) == 3
    assert breadcrumb[0]["id"] == task_a_id
    assert breadcrumb[0]["title"] == "Task A"
    assert breadcrumb[0]["level"] == 0

    assert breadcrumb[1]["id"] == task_b_id
    assert breadcrumb[1]["title"] == "Task B"
    assert breadcrumb[1]["level"] == 1

    assert breadcrumb[2]["id"] == task_c_id
    assert breadcrumb[2]["title"] == "Task C"
    assert breadcrumb[2]["level"] == 2
