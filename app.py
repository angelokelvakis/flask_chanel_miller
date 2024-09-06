from flask import Flask, render_template, request, session, g, send_file, redirect, url_for
import pandas as pd
import sqlite3
import datetime
import io

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Set a secret key for session management

DATABASE = 'submissions.db'


# Utility function to get a connection to the database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Function to execute a query
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# Load passages into the database from a CSV file if necessary
@app.before_request
def load_passages():
    conn = get_db()
    cursor = conn.cursor()

    # Check if passages are already loaded
    cursor.execute('SELECT COUNT(*) FROM passages')
    passage_count = cursor.fetchone()[0]

    if passage_count == 0:
        import pandas as pd
        book_df = pd.read_csv('books.csv')
        for _, row in book_df.iterrows():
            cursor.execute(
                'INSERT INTO passages (passage_id, passage) VALUES (?, ?)',
                (row['Passage_ID'], row['passage'])
            )
        conn.commit()


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
        user_data = query_db('SELECT score FROM submissions WHERE username = ? ORDER BY id DESC LIMIT 1',
                             [username], one=True)
        score = user_data[0] if user_data else 0

        # Retrieve the last passage shown from the session, if available
        if 'last_passage_id' in session:
            passage_id = session['last_passage_id']
            random_passage = query_db('SELECT passage FROM passages WHERE passage_id = ?', [passage_id], one=True)
            passage = random_passage[0] if random_passage else None
        else:
            # Select a random passage
            random_passage = query_db('SELECT passage, passage_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
            passage, passage_id = random_passage
            session['last_passage_id'] = passage_id

        return render_template('index.html', passage=passage, passage_id=session['last_passage_id'], username=username, score=score)

    else:
        # Session error handling
        return render_template('index.html', score=-999)


@app.route('/new_passage')
def new_passage():
    username = session.get('username')  # Retrieve the username from the session
    if not username:
        return redirect(url_for('index'))
    # Get the user's current score
    user_data = query_db('SELECT score FROM submissions WHERE username = ? ORDER BY id DESC LIMIT 1', [username],
                         one=True)
    score = user_data[0] if user_data else 0

    # Generate a new random passage
    random_passage = query_db('SELECT passage, passage_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
    passage, passage_id = random_passage

    # Store the new passage in the session
    session['last_passage_id'] = passage_id

    return render_template('index.html', passage=passage, passage_id=passage_id, score=score)


@app.route('/submit', methods=['POST'])
def submit():
    username = session.get('username')  # Retrieve the username from the session
    if not username:
        return redirect(url_for('index'))
    passage_id = request.form['passage_id']
    category = request.form['category']
    timestamp = datetime.datetime.now()

    # Get the user's current score
    user_data = query_db('SELECT score FROM submissions WHERE username = ? ORDER BY id DESC LIMIT 1', [username],
                         one=True)
    score = user_data[0] + 1 if user_data else 1

    # Add 5 bonus points for every 10th submission
    if score % 10 == 0:
        score += 5

    # Insert the new submission into the database
    conn = get_db()
    conn.execute(
        'INSERT INTO submissions (username, passage_id, category, timestamp, score) VALUES (?, ?, ?, ?, ?)',
        (username, passage_id, category, timestamp, score)
    )
    conn.commit()

    # Select a new random passage
    random_passage = query_db('SELECT passage, passage_id FROM passages ORDER BY RANDOM() LIMIT 1', one=True)
    passage, passage_id = random_passage

    # Store the new passage in the session
    session['last_passage_id'] = passage_id

    return render_template('index.html', passage=passage, passage_id=passage_id, score=score)


@app.route('/download')
def download_data():
    # Query all data from the 'submissions' table
    submissions = query_db('SELECT * FROM submissions')

    # Convert the data into a pandas DataFrame
    df = pd.DataFrame(submissions, columns=['id', 'username', 'passage_id', 'category', 'timestamp', 'score'])

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
