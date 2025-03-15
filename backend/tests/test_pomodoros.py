import pytest
from fastapi import status
from datetime import datetime, timedelta, UTC
from app.db.models import PomodoroSession, Task, PomodoroTaskAssociation


def test_create_pomodoro(authorized_client, test_user):
    # Test creating a pomodoro session
    pomodoro_data = {"duration": 1500, "session_type": "work"}  # 25 minutes

    response = authorized_client.post("/api/v1/pomodoros/", json=pomodoro_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["duration"] == pomodoro_data["duration"]
    assert data["session_type"] == pomodoro_data["session_type"]
    assert data["user_id"] == test_user.id
    assert data["completed"] is False


def test_get_pomodoros(authorized_client, db, test_user):
    # Create some pomodoro sessions
    now = datetime.utcnow()
    pomodoros = [
        PomodoroSession(
            user_id=test_user.id,
            start_time=now - timedelta(hours=2),
            duration=1500,
            session_type="work",
            completed=True,
            end_time=now - timedelta(hours=2) + timedelta(minutes=25),
        ),
        PomodoroSession(
            user_id=test_user.id,
            start_time=now - timedelta(hours=1),
            duration=300,
            session_type="short_break",
            completed=True,
            end_time=now - timedelta(hours=1) + timedelta(minutes=5),
        ),
        PomodoroSession(
            user_id=test_user.id,
            start_time=now,
            duration=1500,
            session_type="work",
            completed=False,
        ),
    ]
    db.add_all(pomodoros)
    db.commit()

    # Get all pomodoros
    response = authorized_client.get("/api/v1/pomodoros/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3

    # Filter by completed
    response = authorized_client.get("/api/v1/pomodoros/?completed=true")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    # Filter by session_type
    response = authorized_client.get("/api/v1/pomodoros/?session_type=work")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2


def test_complete_pomodoro(authorized_client, db, test_user):
    # Create a pomodoro session
    pomodoro = PomodoroSession(
        user_id=test_user.id,
        start_time=datetime.utcnow(),
        duration=1500,
        session_type="work",
        completed=False,
    )
    db.add(pomodoro)
    db.commit()
    db.refresh(pomodoro)

    # Complete the pomodoro
    response = authorized_client.post(f"/api/v1/pomodoros/{pomodoro.id}/complete")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["completed"] is True
    assert data["end_time"] is not None
    assert data["actual_duration"] is not None

    # Verify in database
    db.refresh(pomodoro)
    assert pomodoro.completed is True
    assert pomodoro.end_time is not None


def test_associate_task_with_pomodoro(authorized_client, db, test_user):
    # Create a task
    task = Task(user_id=test_user.id, title="Test Task", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    # Create a pomodoro session
    pomodoro = PomodoroSession(
        user_id=test_user.id,
        start_time=datetime.utcnow(),
        duration=1500,
        session_type="work",
        completed=False,
    )
    db.add(pomodoro)
    db.commit()
    db.refresh(pomodoro)

    # Associate the task with the pomodoro
    association_data = {
        "task_id": task.id,
        "pomodoro_session_id": pomodoro.id,
        "time_spent": 900,  # 15 minutes
        "notes": "Worked on implementation",
    }

    response = authorized_client.post(
        f"/api/v1/pomodoros/{pomodoro.id}/tasks", json=association_data
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["task_id"] == task.id
    assert data["pomodoro_session_id"] == pomodoro.id
    assert data["time_spent"] == association_data["time_spent"]
    assert data["notes"] == association_data["notes"]

    # Get tasks for pomodoro
    response = authorized_client.get(f"/api/v1/pomodoros/{pomodoro.id}/tasks")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["task_id"] == task.id

    # Get pomodoros for task
    response = authorized_client.get(f"/api/v1/pomodoros/task/{task.id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == pomodoro.id


def test_delete_pomodoro(authorized_client, db, test_user):
    # Create a pomodoro session
    pomodoro = PomodoroSession(
        user_id=test_user.id,
        start_time=datetime.utcnow(),
        duration=1500,
        session_type="work",
        completed=False,
    )
    db.add(pomodoro)
    db.commit()
    db.refresh(pomodoro)

    # Create a task
    task = Task(user_id=test_user.id, title="Test Task", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    # Associate the task with the pomodoro
    association = PomodoroTaskAssociation(
        pomodoro_session_id=pomodoro.id, task_id=task.id, time_spent=900
    )
    db.add(association)
    db.commit()

    # Soft delete the pomodoro
    response = authorized_client.delete(f"/api/v1/pomodoros/{pomodoro.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify pomodoro is soft deleted
    db.refresh(pomodoro)
    assert pomodoro.deleted_at is not None

    # Verify association is also soft deleted
    db.refresh(association)
    assert association.deleted_at is not None

    # Pomodoro should not appear in list
    response = authorized_client.get("/api/v1/pomodoros/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 0


@pytest.mark.pomodoro
def test_pomodoro_interruption(authorized_client, db, test_user):
    """Test recording an interruption for a pomodoro session"""
    # Create a pomodoro session
    session_data = {
        "start_time": datetime.now(UTC).isoformat(),
        "duration": 1500,  # 25 minutes
        "session_type": "work",
    }

    response = authorized_client.post("/api/v1/pomodoros/", json=session_data)
    assert response.status_code == status.HTTP_201_CREATED
    session_id = response.json()["id"]

    # Update with interruption
    interruption_data = {
        "end_time": datetime.now(UTC).isoformat(),
        "actual_duration": 600,  # 10 minutes (interrupted early)
        "completed": False,
        "interruption_reason": "Unexpected phone call",
    }

    response = authorized_client.patch(
        f"/api/v1/pomodoros/{session_id}", json=interruption_data
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify the interruption was recorded
    response = authorized_client.get(f"/api/v1/pomodoros/{session_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["completed"] == False
    assert data["interruption_reason"] == "Unexpected phone call"
    assert data["actual_duration"] == 600
