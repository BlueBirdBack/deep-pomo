import pytest
from fastapi import status
from dotenv import load_dotenv
import os
from sqlalchemy import text

# Load test environment variables
load_dotenv(".env.test")


def test_register_user(client):
    # Test user registration
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    # Debug the response if it fails
    if response.status_code != status.HTTP_201_CREATED:
        print(f"Registration failed with status {response.status_code}")
        print(f"Response body: {response.json()}")

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


def test_login_invalid_credentials(client, test_user):
    # Test login with invalid credentials
    login_data = {"username": test_user.username, "password": "wrongpassword"}

    response = client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me(authorized_client, test_user):
    # Test getting current user
    response = authorized_client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


def test_get_me_unauthorized(client):
    # Test getting current user without authentication
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
