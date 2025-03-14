import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from app.main import app
from app.core.auth import get_password_hash, create_access_token
from app.db.models import User, UserSettings
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(".env.test")

# Use the test database URL from environment variables
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://pomo_user:your_password@localhost/deep_pomo_test"
)

print(f"Using test database URL: {SQLALCHEMY_DATABASE_URL}")  # Debug print

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    # Create the database tables
    Base.metadata.drop_all(bind=engine)  # Drop all tables to start with a clean slate
    Base.metadata.create_all(bind=engine)

    # Create a new session for each test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # Clean up after each test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    # Create a test user
    hashed_password = get_password_hash("password123")
    user = User(
        username="testuser", email="testuser@example.com", password_hash=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default settings for the user
    settings = UserSettings(
        user_id=user.id,
        pomodoro_duration=1500,
        short_break_duration=300,
        long_break_duration=900,
        pomodoros_until_long_break=4,
        theme="light",
        notification_enabled=True,
    )
    db.add(settings)
    db.commit()

    return user


@pytest.fixture
def client(db):
    # Override the get_db dependency to use the test database
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def authorized_client(client, test_user):
    # Create a token for the test user
    access_token = create_access_token(data={"sub": test_user.username})
    client.headers = {**client.headers, "Authorization": f"Bearer {access_token}"}
    return client
