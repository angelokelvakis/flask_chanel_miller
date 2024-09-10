import psycopg2
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# PostgreSQL Database config using environment variables
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')


# Function to check database connection
def check_connection():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        print("Connection to the database was successful.")
        conn.close()
    except Exception as e:
        print(f"Error connecting to the database: {e}")


# Function to initialize database and create tables
def init_db():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        cursor = conn.cursor()

        # Create the submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                passage_id TEXT NOT NULL,
                original_id TEXT,
                category TEXT,
                timestamp TIMESTAMPTZ,
                score INTEGER
            )
        ''')

        # Create the passages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS passages (
                passage_id TEXT PRIMARY KEY,
                original_id TEXT,
                passage TEXT
            )
        ''')

        conn.commit()
        print("Tables created successfully.")

        # Print column names from the 'submissions' table
        cursor.execute('''
            SELECT column_name FROM information_schema.columns WHERE table_name = 'submissions';
        ''')
        submissions_columns = cursor.fetchall()
        print("Submissions table columns:", [col[0] for col in submissions_columns])

        # Print column names from the 'passages' table
        cursor.execute('''
            SELECT column_name FROM information_schema.columns WHERE table_name = 'passages';
        ''')
        passages_columns = cursor.fetchall()
        print("Passages table columns:", [col[0] for col in passages_columns])

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error during table creation or querying columns: {e}")
    finally:
        if conn:
            conn.close()


# Run this file to initialize the database
if __name__ == '__main__':
    check_connection()
    init_db()
