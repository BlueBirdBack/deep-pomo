"""Test task endpoints"""

import pytest
from fastapi import status
from app.db.models import Task


@pytest.mark.tasks
def test_create_task(authorized_client, test_user):
    """Test creating a task"""

    task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "high",
        "status": "pending",
    }

    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["priority"] == task_data["priority"]
    assert data["status"] == task_data["status"]
    assert data["user_id"] == test_user.id


@pytest.mark.tasks
def test_create_subtask(authorized_client, db, test_user):
    """Test creating a subtask"""

    # First create a parent task
    parent_task = Task(user_id=test_user.id, title="Parent Task", status="pending")
    db.add(parent_task)
    db.commit()
    db.refresh(parent_task)

    # Now create a subtask
    subtask_data = {"title": "Subtask", "parent_id": parent_task.id}

    response = authorized_client.post("/api/v1/tasks/", json=subtask_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["title"] == subtask_data["title"]
    assert data["parent_id"] == parent_task.id


@pytest.mark.tasks
def test_get_tasks(authorized_client, db, test_user):
    """Test getting tasks"""

    # Create some tasks one by one to allow the trigger to set the path
    task1 = Task(user_id=test_user.id, title="Task 1", status="pending")
    db.add(task1)
    db.commit()

    task2 = Task(user_id=test_user.id, title="Task 2", status="in_progress")
    db.add(task2)
    db.commit()

    task3 = Task(user_id=test_user.id, title="Task 3", status="completed")
    db.add(task3)
    db.commit()

    # Get all tasks
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3

    # Filter by status
    response = authorized_client.get("/api/v1/tasks/?status=in_progress")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Task 2"


@pytest.mark.tasks
def test_get_task(authorized_client, db, test_user):
    """Test getting a task"""

    # Create a task
    task = Task(
        user_id=test_user.id,
        title="Test Task",
        description="This is a test task",
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Get the task
    response = authorized_client.get(f"/api/v1/tasks/{task.id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == task.id
    assert data["title"] == task.title
    assert data["description"] == task.description


@pytest.mark.tasks
def test_update_task(authorized_client, db, test_user):
    """Test updating a task"""

    # Create a task
    task = Task(user_id=test_user.id, title="Original Title", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    # Update the task
    update_data = {"title": "Updated Title", "status": "in_progress"}

    response = authorized_client.put(f"/api/v1/tasks/{task.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["status"] == update_data["status"]

    # Verify in database
    db.refresh(task)
    assert task.title == update_data["title"]
    assert task.status == update_data["status"]


@pytest.mark.tasks
def test_delete_task(authorized_client, db, test_user):
    """Test deleting a task"""

    # Create a task
    task = Task(user_id=test_user.id, title="Task to Delete", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    # Soft delete the task
    response = authorized_client.delete(f"/api/v1/tasks/{task.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify task is soft deleted
    db.refresh(task)
    assert task.deleted_at is not None

    # Task should not appear in list
    response = authorized_client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 0


@pytest.mark.tasks
def test_task_breadcrumb(authorized_client, db, test_user):
    """Test getting a task's breadcrumb"""

    # Create a hierarchy of tasks
    task1 = Task(user_id=test_user.id, title="Task 1", status="pending")
    db.add(task1)
    db.commit()
    db.refresh(task1)

    task2 = Task(
        user_id=test_user.id, title="Task 2", status="pending", parent_id=task1.id
    )
    db.add(task2)
    db.commit()
    db.refresh(task2)

    task3 = Task(
        user_id=test_user.id, title="Task 3", status="pending", parent_id=task2.id
    )
    db.add(task3)
    db.commit()
    db.refresh(task3)

    # Get breadcrumb for task3
    response = authorized_client.get(f"/api/v1/tasks/{task3.id}/breadcrumb")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == task1.id
    assert data[1]["id"] == task2.id
    assert data[2]["id"] == task3.id


@pytest.mark.tasks
def test_task_hierarchy(authorized_client):
    """Test creating a task hierarchy"""

    # Create parent task
    parent_task_data = {
        "title": "Parent Task",
        "description": "This is a parent task",
        "priority": "high",
        "status": "pending",
    }
    parent_response = authorized_client.post("/api/v1/tasks/", json=parent_task_data)
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
    child_id = child_response.json()["id"]

    # Get breadcrumb for child task
    breadcrumb_response = authorized_client.get(f"/api/v1/tasks/{child_id}/breadcrumb")
    assert breadcrumb_response.status_code == status.HTTP_200_OK

    breadcrumb = breadcrumb_response.json()
    assert len(breadcrumb) == 2
    assert breadcrumb[0]["id"] == parent_id
    assert breadcrumb[1]["id"] == child_id


@pytest.mark.tasks
def test_task_status_constraint(authorized_client):
    """Test that invalid task status values are rejected"""
    # Try to create a task with an invalid status
    task_data = {
        "title": "Invalid Status Task",
        "status": "invalid_status",  # Not in the allowed values
    }

    response = authorized_client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Verify the error message mentions status
    error_detail = response.json()["detail"]
    status_error = next(
        (error for error in error_detail if "status" in error["loc"]), None
    )
    assert status_error is not None
