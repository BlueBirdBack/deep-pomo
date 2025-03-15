"""Conftest file for pytest"""

import os
import subprocess
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from app.db.database import get_db
from app.main import app
from app.core.auth import get_password_hash, create_access_token
from app.db.models import User, UserSettings
from dotenv import load_dotenv

# ---- Database Connection Setup ----
# Load test environment variables
load_dotenv(".env.test")

# Use the test database URL from environment variables
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://pomo_user:your_password@localhost/deep_pomo_test"
)

print(f"Using test database URL: {SQLALCHEMY_DATABASE_URL}")  # Debug print

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---- Database Cleaning Functions ----
def clean_database(db_session):
    """Clean all tables in the database"""
    try:
        # Disable foreign key checks temporarily
        db_session.execute(text("SET session_replication_role = 'replica';"))

        # Truncate all tables
        db_session.execute(
            text(
                """
            TRUNCATE users, tasks, pomodoro_sessions, pomodoro_task_associations,
            task_history, user_settings RESTART IDENTITY CASCADE;
        """
            )
        )

        # Re-enable foreign key checks
        db_session.execute(text("SET session_replication_role = 'origin';"))
        db_session.commit()
    finally:
        db_session.close()


# ---- User Creation Functions ----
def create_test_user(db_session):
    """Create a test user with default settings"""
    hashed_password = get_password_hash("password123")
    user = User(
        username="testuser", email="testuser@example.com", password_hash=hashed_password
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

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
    db_session.add(settings)
    db_session.commit()

    return user


# ---- Schema Setup Functions ----
def setup_database_schema():
    """Set up the database schema using schema.sql"""
    load_dotenv(".env.test")
    db_url = os.getenv("TEST_DATABASE_URL")

    # Extract connection parameters from the URL
    db_parts = db_url.replace("postgresql://", "").split("@")
    user_pass = db_parts[0].split(":")
    host_db = db_parts[1].split("/")

    username = user_pass[0]
    password = user_pass[1].split("@")[0]
    host = host_db[0]
    dbname = host_db[1]

    # Set PGPASSWORD environment variable for psql
    os.environ["PGPASSWORD"] = password

    # Run psql to import the schema
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "db", "schema.sql"
    )
    result = subprocess.run(
        ["psql", "-h", host, "-U", username, "-d", dbname, "-f", schema_path],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error importing schema: {result.stderr}")


# ---- Token Generation Functions ----
def generate_auth_token(user):
    """Generate an authentication token for a user"""
    return create_access_token(data={"sub": user.username})


# ---- Pytest Fixtures ----
@pytest.fixture(scope="function")
def db():
    """Create a new database session for each test"""
    # Clean the database before each test
    clean_database(TestingSessionLocal())

    # Create a new session for each test
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db):
    """Create a test user with default settings"""
    return create_test_user(db)


@pytest.fixture
def client():
    """Create a test client for the app"""

    # Create a new session for the test client
    test_db = TestingSessionLocal()

    # Override the get_db dependency to use the test database
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    test_db.close()


@pytest.fixture
def authorized_client(client, test_user):
    """Create an authorized client for the test user"""
    # Create a token for the test user
    access_token = generate_auth_token(test_user)
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {access_token}",
    }
    return client


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure the test database has the schema loaded"""
    setup_database_schema()
    yield
