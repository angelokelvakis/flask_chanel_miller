from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import random
import datetime

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Load the book passages from the CSV file
book_df = pd.read_csv('books.csv')

# File to store the submissions
submissions_file = 'submissions.csv'

# Ensure the submissions file exists with the correct headers
try:
    submissions_df = pd.read_csv(submissions_file)
except FileNotFoundError:
    submissions_df = pd.DataFrame(columns=['username', 'passage_id', 'category', 'timestamp', 'score'])
    submissions_df.to_csv(submissions_file, index=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        session['username'] = username  # Store the username in the session

        if not username:
            return render_template('index.html', error="Username is required")

        # Get the user's current score
        user_data = submissions_df[submissions_df['username'] == username]
        if not user_data.empty:
            score = user_data.iloc[-1]['score']
        else:
            score = 0

        # Select a random passage
        random_passage = book_df.sample().iloc[0]
        passage = random_passage['passage']
        passage_id = random_passage['Passage_ID']

        return render_template('index.html', passage=passage, passage_id=passage_id, username=username, score=score)

    return render_template('index.html', score=0)


@app.route('/new_passage')
def new_passage():
    # Generate a new random passage
    random_passage = book_df.sample().iloc[0]
    passage = random_passage['passage']
    passage_id = random_passage['Passage_ID']
    return render_template('index.html', passage=passage, passage_id=passage_id)


@app.route('/submit', methods=['POST'])
def submit():
    username = session.get('username')  # Retrieve the username from the session
    passage_id = request.form['passage_id']
    category = request.form['category']
    timestamp = datetime.datetime.now()

    # Ensure the submissions file exists with the correct headers
    try:
        submissions_df = pd.read_csv(submissions_file)
    except FileNotFoundError:
        submissions_df = pd.DataFrame(columns=['username', 'passage_id', 'category', 'timestamp', 'score'])
        submissions_df.to_csv(submissions_file, index=False)

    # Retrieve the current user's score
    user_data = submissions_df[submissions_df['username'] == username]
    if not user_data.empty:
        score = user_data.iloc[-1]['score'] + 1
    else:
        score = 1

    # Add 5 bonus points for every 10th submission
    if score % 10 == 0:
        score += 5

    # Save the submission to the CSV file
    new_submission = pd.DataFrame({
        'username': [username],
        'passage_id': [passage_id],
        'category': [category],
        'timestamp': [timestamp],
        'score': [score]
    })

    new_submission.to_csv(submissions_file, mode='a', header=False, index=False)

    # Select a new random passage
    random_passage = book_df.sample().iloc[0]
    passage = random_passage['passage']
    passage_id = random_passage['Passage_ID']

    return render_template('index.html', passage=passage, passage_id=passage_id, score=score)


if __name__ == '__main__':
    app.run(debug=True)
