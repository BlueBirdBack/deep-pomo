"""Utility functions for cleaning test database."""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, find_dotenv
from test_conf_setup_schema import get_db_connection_info

# Load test environment variables
load_dotenv(find_dotenv(".env.test"))


def verify_tables_exist():
    """Check if tables exist in the database."""
    conn_info = get_db_connection_info()
    if not conn_info:
        return False

    engine = create_engine(conn_info["db_url"])
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        result = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'users'
                );
                """
            )
        )
        tables_exist = result.scalar()
        return tables_exist
    except Exception as e:  # pylint: disable=W0718
        print(f"Error checking tables: {e}")
        return False
    finally:
        session.close()


def truncate_all_tables():
    """Truncate all tables in the database."""
    conn_info = get_db_connection_info()
    if not conn_info:
        return False

    engine = create_engine(conn_info["db_url"])
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    try:
        # Truncate all tables with CASCADE option
        session.execute(
            text(
                """
                TRUNCATE users, tasks, pomodoro_sessions, pomodoro_task_associations,
                task_history, user_settings RESTART IDENTITY CASCADE;
                """
            )
        )
        session.commit()
        return True
    except Exception as e:  # pylint: disable=W0718
        print(f"Error truncating tables: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def clean_test_database():
    """Clean the test database by truncating all tables."""
    print("Checking if tables exist...")

    if not verify_tables_exist():
        print("Tables don't exist yet. Nothing to clean.")
        return True

    print("Truncating all tables...")
    if truncate_all_tables():
        print("All tables truncated successfully!")
        return True

    return False


if __name__ == "__main__":
    if clean_test_database():
        sys.exit(0)
    else:
        sys.exit(1)
