import pytest
from fastapi import status
from datetime import datetime
from app.db.models import Task


def test_create_hierarchical_tasks(authorized_client, test_user, db):
    """Test creating tasks with parent-child relationships"""
    # Create parent task
    parent_task_data = {
        "title": "Parent Task",
        "description": "This is a parent task",
        "priority": "high",
        "status": "pending",
    }
    parent_response = authorized_client.post("/api/v1/tasks/", json=parent_task_data)
    assert parent_response.status_code == status.HTTP_201_CREATED
    parent_id = parent_response.json()["id"]

    # Create child task
    child_task_data = {
        "title": "Child Task",
        "description": "This is a child task",
        "priority": "medium",
        "status": "pending",
        "parent_id": parent_id,
    }
    child_response = authorized_client.post("/api/v1/tasks/", json=child_task_data)
    assert child_response.status_code == status.HTTP_201_CREATED
    child_id = child_response.json()["id"]

    # Create grandchild task
    grandchild_task_data = {
        "title": "Grandchild Task",
        "description": "This is a grandchild task",
        "priority": "low",
        "status": "pending",
        "parent_id": child_id,
    }
    grandchild_response = authorized_client.post(
        "/api/v1/tasks/", json=grandchild_task_data
    )
    assert grandchild_response.status_code == status.HTTP_201_CREATED

    # Verify paths were correctly set by LTREE
    parent_task = db.query(Task).filter(Task.id == parent_id).first()
    child_task = db.query(Task).filter(Task.id == child_id).first()
    grandchild_task = (
        db.query(Task).filter(Task.id == grandchild_response.json()["id"]).first()
    )

    assert parent_task.path == str(parent_id)
    assert child_task.path == f"{parent_id}.{child_id}"
    assert grandchild_task.path == f"{parent_id}.{child_id}.{grandchild_task.id}"


def test_get_task_children(authorized_client, test_user, db):
    """Test retrieving all children of a task"""
    # Create parent task
    parent_task_data = {"title": "Parent Task", "status": "pending"}
    parent_response = authorized_client.post("/api/v1/tasks/", json=parent_task_data)
    parent_id = parent_response.json()["id"]

    # Create several child tasks
    for i in range(3):
        child_task_data = {
            "title": f"Child Task {i+1}",
            "status": "pending",
            "parent_id": parent_id,
        }
        authorized_client.post("/api/v1/tasks/", json=child_task_data)

    # Create a nested child
    child_response = authorized_client.post(
        "/api/v1/tasks/",
        json={"title": "Child Task 1", "status": "pending", "parent_id": parent_id},
    )
    child_id = child_response.json()["id"]

    authorized_client.post(
        "/api/v1/tasks/",
        json={"title": "Grandchild Task", "status": "pending", "parent_id": child_id},
    )

    # Get children of parent task
    response = authorized_client.get(f"/api/v1/tasks/{parent_id}/children")
    assert response.status_code == status.HTTP_200_OK
    children = response.json()

    # Should have 4 direct children
    assert len(children) == 4


def test_prevent_circular_references(authorized_client, test_user):
    """Test prevention of circular references in task hierarchy"""
    # Create two tasks
    task1_data = {"title": "Task 1", "status": "pending"}
    task1_response = authorized_client.post("/api/v1/tasks/", json=task1_data)
    task1_id = task1_response.json()["id"]

    task2_data = {"title": "Task 2", "status": "pending", "parent_id": task1_id}
    task2_response = authorized_client.post("/api/v1/tasks/", json=task2_data)
    task2_id = task2_response.json()["id"]

    # Try to make task1 a child of task2, creating a circular reference
    update_data = {"parent_id": task2_id}
    response = authorized_client.patch(f"/api/v1/tasks/{task1_id}", json=update_data)

    # Should fail with a 400 error
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "circular reference" in response.json()["detail"].lower()
