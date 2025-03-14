import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base, get_db
from app.main import app
from app.core.auth import get_password_hash
from app.db.models import User, UserSettings

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)

    # Create a new session for each test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
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

    # Reset the dependency override
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def test_user(db):
    # Create a test user
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default settings for the user
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    db.commit()

    return user


@pytest.fixture(scope="function")
def token(client, test_user):
    # Get a token for the test user
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user.username, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def authorized_client(client, token):
    # Create a client with authorization headers
    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return client
