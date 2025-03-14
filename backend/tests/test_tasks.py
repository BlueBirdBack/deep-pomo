import pytest
from fastapi import status
from app.db.models import Task


def test_create_task(authorized_client, test_user):
    # Test creating a task
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


def test_create_subtask(authorized_client, db, test_user):
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


def test_get_tasks(authorized_client, db, test_user):
    # Create some tasks
    tasks = [
        Task(user_id=test_user.id, title="Task 1", status="pending"),
        Task(user_id=test_user.id, title="Task 2", status="in_progress"),
        Task(user_id=test_user.id, title="Task 3", status="completed"),
    ]
    db.add_all(tasks)
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


def test_get_task(authorized_client, db, test_user):
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


def test_update_task(authorized_client, db, test_user):
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


def test_delete_task(authorized_client, db, test_user):
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


def test_task_breadcrumb(authorized_client, db, test_user):
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
