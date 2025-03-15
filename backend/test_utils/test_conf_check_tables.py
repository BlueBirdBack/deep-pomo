"""This script checks the tables in the database."""

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


def check_tables():
    """Check the tables in the database."""
    print("Checking database tables...")

    try:
        # Try to establish a connection using the URL
        conn = psycopg2.connect(database_url)

        # Get server version
        cur = conn.cursor()

        # Check for tables and data
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [row[0] for row in cur.fetchall()]

        print(f"\nTables in database: {tables}")

        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"Table {table}: {count} rows")

            # If there's data, show a sample
            if count > 0:
                cur.execute(f"SELECT * FROM {table} LIMIT 5")
                sample = cur.fetchall()
                print(f"Sample data from {table}:")
                for row in sample:
                    print(f"  {row}")

        # Close connection
        cur.close()
        conn.close()

        return True

    except Exception as e:  # pylint: disable=W0718
        print("\nError checking tables!")
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    if check_tables():
        print("\nDatabase tables check completed successfully!")
        sys.exit(0)
    else:
        print("\nDatabase tables check failed!")
        sys.exit(1)
