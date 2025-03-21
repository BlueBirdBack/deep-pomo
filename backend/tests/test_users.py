"""Test user profile and settings endpoints"""

import pytest
from fastapi import status


@pytest.mark.users
def test_update_user(authorized_client, test_user):
    """Test updating user profile"""
    update_data = {"username": "updateduser", "email": "updated@example.com"}

    response = authorized_client.put("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["email"] == update_data["email"]
    assert data["id"] == test_user.id


@pytest.mark.users
def test_get_user_settings(authorized_client, test_user):
    """Test retrieving user settings"""
    response = authorized_client.get("/api/v1/users/me/settings")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user_id"] == test_user.id
    assert "pomodoro_duration" in data
    assert "theme" in data


@pytest.mark.users
def test_update_user_settings(authorized_client, test_user):
    """Test updating user settings"""
    settings_data = {"pomodoro_duration": 1800, "theme": "dark"}  # 30 minutes

    response = authorized_client.put("/api/v1/users/me/settings", json=settings_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["pomodoro_duration"] == settings_data["pomodoro_duration"]
    assert data["theme"] == settings_data["theme"]
    assert data["user_id"] == test_user.id


@pytest.mark.users
def test_user_settings_defaults(authorized_client, db, test_user):
    """Test that user settings have correct default values from schema"""
    # Get user settings without modifying them first
    response = authorized_client.get("/api/v1/users/me/settings")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    # Verify defaults match schema.sql definitions
    assert data["pomodoro_duration"] == 1500  # 25 minutes in seconds
    assert data["short_break_duration"] == 300  # 5 minutes
    assert data["long_break_duration"] == 900  # 15 minutes
    assert data["pomodoros_until_long_break"] == 4
    assert data["theme"] == "light"
    assert data["notification_enabled"] is True
