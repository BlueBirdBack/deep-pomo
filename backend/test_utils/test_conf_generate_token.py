"""This script generates a test token for the test user."""

import sys
import os
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


def generate_test_token():
    """Generate a test token for the test user."""
    # Get database URL from environment variables
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        print("TEST_DATABASE_URL not found in environment variables")
        return False

    try:
        # Import here to avoid circular imports
        # pylint: disable=C0415
        # type: ignore
        from app.core.auth import create_access_token  # type: ignore
        from app.db.models import User  # type: ignore

        # pylint: enable=C0415

        # Create engine and session
        engine = create_engine(database_url)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
        db = TestingSessionLocal()

        try:
            # Find the test user
            user = db.query(User).filter(User.username == "testuser").first()

            if not user:
                print("Test user not found. Please run create_test_user.py first.")
                return False

            # Create a token for the test user
            access_token = create_access_token(data={"sub": user.username})

            print(f"\nTest user found: {user.username}")
            print(f"Generated access token: {access_token}")
            print("\nUse this token in the Authorization header:")
            print(f"Authorization: Bearer {access_token}")

            return True

        except Exception as e:  # pylint: disable=W0718
            print(f"Error generating token: {e}")
            return False
        finally:
            db.close()

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this script from the project root directory")
        return False


if __name__ == "__main__":
    if generate_test_token():
        sys.exit(0)
    else:
        sys.exit(1)
