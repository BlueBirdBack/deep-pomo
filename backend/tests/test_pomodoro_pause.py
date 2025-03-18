import pytest
from fastapi import status
from datetime import datetime, timedelta, UTC
from sqlalchemy import text
from time import sleep


def test_pause_resume_pomodoro(authorized_client, db, test_user):
    """Test pausing and resuming a pomodoro session"""
    # Create a pomodoro session
    pomodoro_data = {
        "start_time": datetime.now(UTC).isoformat(),
        "duration": 1500,  # 25 minutes
        "session_type": "work",
    }
    response = authorized_client.post("/api/v1/pomodoros/", json=pomodoro_data)
    assert response.status_code == status.HTTP_201_CREATED
    pomodoro_id = response.json()["id"]

    # Pause the pomodoro
    response = authorized_client.post(f"/api/v1/pomodoros/{pomodoro_id}/pause")
    assert response.status_code == status.HTTP_200_OK

    # Sleep for a short time to ensure pause duration is measurable
    sleep(1)

    # Resume the pomodoro
    response = authorized_client.post(f"/api/v1/pomodoros/{pomodoro_id}/resume")
    assert response.status_code == status.HTTP_200_OK

    # Check pause stats again
    response = authorized_client.get(f"/api/v1/pomodoros/{pomodoro_id}/pause-stats")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_paused"] is False
    assert response.json()["total_pause_duration"] > 0


def test_preset_pomodoro(authorized_client, db, test_user):
    """Test creating a preset pomodoro session based on user settings"""
    # Create a work session
    response = authorized_client.post("/api/v1/pomodoros/preset?session_type=work")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "work"

    # Create a short break session
    response = authorized_client.post(
        "/api/v1/pomodoros/preset?session_type=short_break"
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "short_break"

    # Create a long break session
    response = authorized_client.post(
        "/api/v1/pomodoros/preset?session_type=long_break"
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "long_break"
