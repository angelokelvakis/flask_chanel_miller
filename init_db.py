import sqlite3


# Create the SQLite database and set up tables
def init_db():
    conn = sqlite3.connect('submissions.db')
    cursor = conn.cursor()

    # Create the submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            passage_id TEXT,
            original_id TEXT,
            category TEXT,
            timestamp TEXT,
            score INTEGER
        )
    ''')

    # Create the passages table if needed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passages (
            passage_id TEXT PRIMARY KEY,
            original_id TEXT,
            passage TEXT
        )
    ''')

    conn.commit()
    conn.close()


# Run this file to initialize the database
if __name__ == '__main__':
    init_db()