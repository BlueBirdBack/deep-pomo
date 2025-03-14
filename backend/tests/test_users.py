import pytest
from fastapi import status


def test_register_user(client):
    # Test user registration
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "id" in data


def test_login(client, test_user):
    # Test login
    login_data = {"username": test_user.username, "password": "password123"}

    response = client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_me(authorized_client, test_user):
    # Test getting current user
    response = authorized_client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


def test_update_user(authorized_client, test_user):
    # Test updating user
    update_data = {"username": "updateduser", "email": "updated@example.com"}

    response = authorized_client.put("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["email"] == update_data["email"]


def test_get_user_settings(authorized_client, test_user):
    # Test getting user settings
    response = authorized_client.get("/api/v1/users/me/settings")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user_id"] == test_user.id
    assert "pomodoro_duration" in data
    assert "theme" in data


def test_update_user_settings(authorized_client, test_user):
    # Test updating user settings
    settings_data = {"pomodoro_duration": 1800, "theme": "dark"}  # 30 minutes

    response = authorized_client.put("/api/v1/users/me/settings", json=settings_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["pomodoro_duration"] == settings_data["pomodoro_duration"]
    assert data["theme"] == settings_data["theme"]
