"""Test pausing and resuming a pomodoro session"""

from datetime import datetime, UTC
from time import sleep
import pytest
from fastapi import status
from app.db.models import (
    PomodoroSession,
    PomodoroSessionInterruption,
    UserSettings,
)


@pytest.mark.pomodoro
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

    # Verify pomodoro was created with correct user_id using db
    db_pomodoro = (
        db.query(PomodoroSession).filter(PomodoroSession.id == pomodoro_id).first()
    )
    assert db_pomodoro is not None
    assert db_pomodoro.user_id == test_user.id
    assert db_pomodoro.session_type == "work"

    # Pause the pomodoro
    response = authorized_client.post(f"/api/v1/pomodoros/{pomodoro_id}/pause")
    assert response.status_code == status.HTTP_200_OK

    # Sleep for a short time to ensure pause duration is measurable
    sleep(1)

    # Resume the pomodoro
    response = authorized_client.post(f"/api/v1/pomodoros/{pomodoro_id}/resume")
    assert response.status_code == status.HTTP_200_OK

    # Check pause state in database
    interruptions = (
        db.query(PomodoroSessionInterruption)
        .filter(PomodoroSessionInterruption.pomodoro_session_id == pomodoro_id)
        .all()
    )
    assert len(interruptions) > 0
    assert interruptions[-1].resumed_at is not None  # Should be resumed

    # Get pause stats from the API
    stats_response = authorized_client.get(
        f"/api/v1/pomodoros/{pomodoro_id}/pause-stats"
    )
    assert stats_response.status_code == status.HTTP_200_OK
    pause_stats = stats_response.json()

    # Verify total_pause_duration in database matches API response
    db_total_pause = sum(
        int((i.resumed_at - i.paused_at).total_seconds())
        for i in interruptions
        if i.resumed_at is not None
    )
    assert db_total_pause == pause_stats["total_pause_duration"]


@pytest.mark.pomodoro
def test_preset_pomodoro(authorized_client, db, test_user):
    """Test creating a preset pomodoro session based on user settings"""
    # Get user settings to verify against
    user_settings = (
        db.query(UserSettings).filter(UserSettings.user_id == test_user.id).first()
    )
    assert user_settings is not None

    # Create a work session
    response = authorized_client.post("/api/v1/pomodoros/preset?session_type=work")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "work"

    # Verify duration matches user settings and belongs to correct user
    work_pomodoro = (
        db.query(PomodoroSession).filter(PomodoroSession.id == data["id"]).first()
    )
    assert work_pomodoro is not None
    assert work_pomodoro.user_id == test_user.id
    assert work_pomodoro.duration == user_settings.pomodoro_duration

    # Create a short break session
    response = authorized_client.post(
        "/api/v1/pomodoros/preset?session_type=short_break"
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "short_break"

    # Verify short break session in database
    short_break = (
        db.query(PomodoroSession).filter(PomodoroSession.id == data["id"]).first()
    )
    assert short_break is not None
    assert short_break.user_id == test_user.id
    assert short_break.duration == user_settings.short_break_duration

    # Create a long break session
    response = authorized_client.post(
        "/api/v1/pomodoros/preset?session_type=long_break"
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["session_type"] == "long_break"

    # Verify long break session in database
    long_break = (
        db.query(PomodoroSession).filter(PomodoroSession.id == data["id"]).first()
    )
    assert long_break is not None
    assert long_break.user_id == test_user.id
    assert long_break.duration == user_settings.long_break_duration
