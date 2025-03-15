"""Utility functions for testing database connection."""

import sys
import os
import psycopg2
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env.test
load_dotenv(find_dotenv(".env.test"))

# Get database URL from environment variables
database_url = os.getenv("TEST_DATABASE_URL")
if not database_url:
    print("TEST_DATABASE_URL not found in environment variables")
    sys.exit(1)

# print(f"Using database URL from environment: {database_url}")


def test_connection():
    """Test the connection to the database."""
    print("Attempting to connect to PostgreSQL using DATABASE_URL")

    try:
        # Try to establish a connection using the URL
        conn = psycopg2.connect(database_url)

        # Get server version
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]

        print("\nConnection successful!")
        print(f"PostgreSQL version: {version}")

        # Close connection
        cur.close()
        conn.close()

        return True

    except Exception as e:  # pylint: disable=W0718
        print("\nConnection failed!")
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    if test_connection():
        print("Database connection test passed!")
        sys.exit(0)
    else:
        print("Database connection test failed!")
        sys.exit(1)
