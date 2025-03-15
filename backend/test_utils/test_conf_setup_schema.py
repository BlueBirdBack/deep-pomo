"""Utility functions for setting up test database schema."""

import subprocess
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, find_dotenv

# Load test environment variables
load_dotenv(find_dotenv(".env.test"))


def get_db_connection_info():
    """Extract database connection parameters from environment variables."""
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        print("TEST_DATABASE_URL not found in environment variables")
        return None

    # Extract connection parameters from the URL
    db_parts = db_url.replace("postgresql://", "").split("@")
    user_pass = db_parts[0].split(":")
    host_db = db_parts[1].split("/")

    return {
        "db_url": db_url,
        "username": user_pass[0],
        "password": user_pass[1].split("@")[0],
        "host": host_db[0],
        "dbname": host_db[1],
    }


def find_schema_path():
    """Find the path to the schema.sql file."""
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    while (
        os.path.basename(current_dir) != "backend"
        and os.path.dirname(current_dir) != current_dir
    ):
        current_dir = os.path.dirname(current_dir)

    print(f"Current directory: {current_dir}")
    return os.path.join(current_dir, "db", "schema.sql")


def reset_schema(host, dbname, username, user_to_connect):
    """Reset the database schema."""
    schema_setup = subprocess.run(
        [
            "psql",
            "-h",
            host,
            "-U",
            user_to_connect,
            "-d",
            dbname,
            "-c",
            "DROP SCHEMA IF EXISTS public CASCADE; "
            "CREATE SCHEMA public; "
            "ALTER SCHEMA public OWNER TO " + username + "; "
            "GRANT ALL ON SCHEMA public TO public; "
            "GRANT ALL ON SCHEMA public TO " + username + ";",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if schema_setup.returncode != 0:
        print(f"Error setting up schema: {schema_setup.stderr}")
        return False
    return True


def import_schema(host, username, dbname, schema_path):
    """Import the schema from the SQL file."""
    # Set search path
    set_search_path = subprocess.run(
        [
            "psql",
            "-h",
            host,
            "-U",
            username,
            "-d",
            dbname,
            "-c",
            "SET search_path TO public;",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if set_search_path.returncode != 0:
        print(f"Error setting search path: {set_search_path.stderr}")
        return False

    # Import schema
    result = subprocess.run(
        ["psql", "-h", host, "-U", username, "-d", dbname, "-f", schema_path],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error importing schema: {result.stderr}")
        return False

    print("Schema import command completed. Checking if tables were created...")
    print(f"Command output: {result.stdout}")
    print(f"Command errors: {result.stderr}")
    return True


def verify_tables(db_url):
    """Verify that tables were created successfully."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        table_check = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'users'
                );
            """
            )
        )
        tables_exist = table_check.scalar()

        if tables_exist:
            print("Tables verified! Schema was successfully imported.")
            return True

        print("ERROR: Tables were not created despite successful import command.")
        print("Check your schema.sql file for errors or schema name issues.")
        return False
    except Exception as e:  # pylint: disable=W0718
        print(f"Error verifying tables: {e}")
        return False
    finally:
        session.close()


def setup_test_schema():
    """Ensure the test database has the schema loaded"""
    # Get connection info
    conn_info = get_db_connection_info()
    if not conn_info:
        return False

    # Find schema path
    schema_path = find_schema_path()
    print(f"Importing schema from: {schema_path}")

    # Set password for psql
    os.environ["PGPASSWORD"] = conn_info["password"]

    try:
        # Determine user to connect as
        superuser = os.getenv("POSTGRES_SUPERUSER", "postgres")
        superuser_password = os.getenv("POSTGRES_SUPERUSER_PASSWORD", "")

        if superuser_password:
            os.environ["PGPASSWORD"] = superuser_password
            user_to_connect = superuser
        else:
            user_to_connect = conn_info["username"]

        # Check schema permissions
        subprocess.run(
            [
                "psql",
                "-h",
                conn_info["host"],
                "-U",
                user_to_connect,
                "-d",
                conn_info["dbname"],
                "-c",
                "SELECT schema_name, schema_owner FROM information_schema.schemata "
                "WHERE schema_name = 'public';",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Reset schema
        if not reset_schema(
            conn_info["host"],
            conn_info["dbname"],
            conn_info["username"],
            user_to_connect,
        ):
            return False

        # Reset password for the main user
        os.environ["PGPASSWORD"] = conn_info["password"]
    except Exception as e:  # pylint: disable=W0718
        print(f"Error during schema setup: {e}")
        return False

    # Import schema
    if not import_schema(
        conn_info["host"], conn_info["username"], conn_info["dbname"], schema_path
    ):
        return False

    # Verify tables
    return verify_tables(conn_info["db_url"])


if __name__ == "__main__":
    if setup_test_schema():
        sys.exit(0)
    else:
        sys.exit(1)
