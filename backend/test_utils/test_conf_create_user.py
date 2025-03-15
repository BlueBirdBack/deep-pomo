"""Utility functions for creating a test user"""

import sys
import os
import random
import string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, find_dotenv

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))

# Add both project root and backend directory to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load test environment variables
load_dotenv(find_dotenv(".env.test"))


def generate_random_string(length=8):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase + string.digits
    return "".join(random.choice(letters) for _ in range(length))


def get_test_db_session():
    """Create and return a database session for testing"""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        print("TEST_DATABASE_URL not found in environment variables")
        return None

    try:
        engine = create_engine(database_url)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
        return TestingSessionLocal()
    except Exception as e:  # pylint: disable=W0718
        print(f"Error creating database session: {e}")
        return None


def create_test_user():
    """Create a test user with random credentials and default settings"""
    try:
        # pylint: disable=C0415
        # type: ignore
        from app.core.auth import get_password_hash  # type: ignore
        from app.db.models import User, UserSettings  # type: ignore

        # pylint: enable=C0415

        # Get database session
        db = get_test_db_session()
        if not db:
            return False

        try:
            # Generate random username, email and password
            random_suffix = generate_random_string()
            username = f"testuser_{random_suffix}"
            email = f"testuser_{random_suffix}@example.com"
            password = f"password_{random_suffix}"

            # Create a test user
            print(f"Creating test user: {username}...")
            hashed_password = get_password_hash(password)
            user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            print(f"Test user created with ID: {user.id}")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Password: {password}")

            # Create default settings for the user
            print("Creating user settings...")
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

            print("User settings created successfully!")
            return True

        except Exception as e:  # pylint: disable=W0718
            print(f"Error creating test user: {e}")
            return False
        finally:
            db.close()

    except ImportError as e:
        print(f"Import error: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        print("Make sure you're running this script from the project root directory")
        return False


if __name__ == "__main__":
    if create_test_user():
        sys.exit(0)
    else:
        sys.exit(1)
