from flask import Flask, render_template, request, session, g, send_file, redirect, url_for
import pandas as pd
import datetime
import io
import os
import psycopg2
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# PostgreSQL Database config using environment variables
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Set a secret key for session management


# Utility function to get a connection to the PostgreSQL database
def get_db():
    if '_database' not in g:
        g._database = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
    return g._database


@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()


# Function to execute a query
def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    conn.commit()
    return (rv[0] if rv else None) if one else rv


@app.before_request
def load_passages():
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Check if passages are already loaded
        cursor.execute('SELECT COUNT(*) FROM passages')
        passage_count = cursor.fetchone()[0]
    except psycopg2.Error as e:
        # Log the error and return if the table does not exist
        print(f"Error querying the passages table: {e}")
        return

    if passage_count == 0:
        try:
            book_df = pd.read_csv('books.csv')
            for _, row in book_df.iterrows():
                cursor.execute(
                    'INSERT INTO passages (passage_id, original_id, passage) VALUES (%s, %s, %s)',
                    (row['Passage_ID'], row['original_id'], row['passage'])
                )
            conn.commit()
            print(f"Successfully loaded {len(book_df)} passages into the database.")
        except Exception as e:
            print(f"Error loading passages from CSV: {e}")
        finally:
            cursor.close()  # Make sure to close the cursor after use


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        if not username:
            return render_template('index.html', error="Username is required")

        session['username'] = username  # Store the username in the session

    # Handle GET requests or after POST submission
    username = session.get('username')

    if username:
        # Get the user's current score
        user_data = query_db('SELECT score FROM submissions WHERE username = %s ORDER BY id DESC LIMIT 1',
                             [username], one=True)
        score = user_data[0] if user_data else 0

        # Retrieve the last passage shown from the session, if available
        if 'last_passage_id' in session:
            passage_id = session['last_passage_id']
            random_passage = query_db('SELECT passage, original_id FROM passages WHERE passage_id = %s', [passage_id], one=True)
            passage = random_passage[0] if random_passage else None
            original_id = random_passage[1] if random_passage else None
        else:
            # Select a random passage
            random_passage = query_db('SELECT passage, passage_id, original_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
            passage, passage_id, original_id = random_passage
            session['last_passage_id'] = passage_id

        # Query for total number of passages
        total_p = query_db('SELECT COUNT(*) FROM passages', one=True)[0]
        # Query for the number of unique classified passages
        class_p = query_db('SELECT COUNT(DISTINCT passage_id) FROM submissions', one=True)[0]
        # Calculate the percentage completion
        progress = round((int(class_p) / int(total_p)) * 100, 2) if total_p else 0

        return render_template('index.html',
                               passage=passage,
                               passage_id=session['last_passage_id'],
                               original_id=original_id,
                               username=username,
                               score=score,
                               progress=progress)

    else:
        # Session error handling
        return render_template('index.html', score=-999)


@app.route('/new_passage')
def new_passage():
    username = session.get('username')  # Retrieve the username from the session
    if not username:
        return redirect(url_for('index'))
    # Get the user's current score
    user_data = query_db('SELECT score FROM submissions WHERE username = %s ORDER BY id DESC LIMIT 1', [username],
                         one=True)
    score = user_data[0] if user_data else 0

    # Generate a new random passage
    random_passage = query_db('SELECT passage, passage_id, original_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
    passage, passage_id, original_id = random_passage

    # Store the new passage in the session
    session['last_passage_id'] = passage_id

    # Query for total number of passages
    total_p = query_db('SELECT COUNT(*) FROM passages', one=True)[0]
    # Query for the number of unique classified passages
    class_p = query_db('SELECT COUNT(DISTINCT passage_id) FROM submissions', one=True)[0]
    # Calculate the percentage completion
    progress = round((int(class_p) / int(total_p)) * 100, 2) if total_p else 0

    return render_template('index.html',
                           passage=passage,
                           passage_id=passage_id,
                           original_id=original_id,
                           score=score,
                           progress=progress)


@app.route('/submit', methods=['POST'])
def submit():
    username = session.get('username')  # Retrieve the username from the session
    if not username:
        return redirect(url_for('index'))
    passage_id = request.form['passage_id']
    original_id = request.form['original_id']
    category = request.form['category']
    timestamp = datetime.datetime.now()

    # Get the user's current score
    user_data = query_db('SELECT score FROM submissions WHERE username = %s ORDER BY id DESC LIMIT 1', [username],
                         one=True)
    score = user_data[0] + 1 if user_data else 1

    # Add 5 bonus points for every 10th submission
    if score % 10 == 0:
        score += 5

    # Insert the new submission into the database
    conn = get_db()
    # Create a cursor
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO submissions (username, passage_id, original_id, category, timestamp, score) VALUES (%s, %s, %s, %s, %s, %s)',
        (username, passage_id, original_id, category, timestamp, score)
    )
    conn.commit()

    # Select a new random passage
    random_passage = query_db('SELECT passage, passage_id, original_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
    passage, passage_id, original_id = random_passage

    # Store the new passage in the session
    session['last_passage_id'] = passage_id

    # Query for total number of passages
    total_p = query_db('SELECT COUNT(*) FROM passages', one=True)[0]
    # Query for the number of unique classified passages
    class_p = query_db('SELECT COUNT(DISTINCT passage_id) FROM submissions', one=True)[0]
    # Calculate the percentage completion
    progress = round((int(class_p) / int(total_p)) * 100, 2) if total_p else 0

    return render_template('index.html',
                           passage=passage,
                           passage_id=passage_id,
                           original_id=original_id,
                           score=score,
                           progress=progress)


@app.route('/download')
def download_data():
    # Query all data from the 'submissions' table
    submissions = query_db('SELECT * FROM submissions')

    # Convert the data into a pandas DataFrame
    df = pd.DataFrame(submissions, columns=['id', 'username', 'passage_id', 'original_id', 'category', 'timestamp', 'score'])

    # Use StringIO to create a file-like object in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)  # Move the pointer to the start of the file

    # Send the file back as an attachment (CSV format)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='submissions.csv')


if __name__ == '__main__':
    app.run(debug=True)
