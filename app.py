from flask import Flask, request, render_template, redirect, url_for, session
import google.generativeai as genai
import os
from flask_session import Session

app = Flask(__name__)

# Secret key and session configuration
app.secret_key = "Panskbd"
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to store session data
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True  # To ensure session data is secure

# Initialize Flask-Session
Session(app)

# Google Gemini API setup
gemini = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=gemini)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_review_from_gemini(question, answer):
    """Generates a review for the given answer based on the question using Gemini."""
    prompt = (
        "Based on the following interview question and candidate's answer, provide feedback on the quality of the answer:\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        "Provide your feedback about the answer. Suggest areas for improvement and highlight the strengths."
    )
    try:
        # Send the prompt to Gemini and get the response
        inputs = model.generate_content(prompt)
        review = inputs.text.strip()  # Get the review text
        return review
    except Exception as e:
        print(f"Error while generating review: {e}")
        return "There was an issue generating feedback. Please try again later."

def generate_questions(job_description, candidate_profile):
    """Generates interview questions based on job description and candidate profile."""
    prompt = (
        "Based on the following job description and candidate profile, generate interview questions:\n\n"
        f"Job Description: {job_description}\n"
        f"Candidate Profile: {candidate_profile}\n\n"
        "Only give 5 questions"
        "START WITH THE QUESTIONS DIRECTLY AND DONT GIVE YOUR INSIGHTS ON THE QUESTION"
    )
    inputs = model.generate_content(prompt)
    questions = inputs.text.split('\n')  # Questions are separated by new lines
    return questions

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        job_description = request.form['job_description']
        candidate_profile = request.form['candidate_profile']

        if job_description and candidate_profile:
            questions = generate_questions(job_description, candidate_profile)
            session['questions'] = questions
            session['question_index'] = 0
            session['answers'] = []  # Clear answers
            session['reviews'] = []  # Clear reviews
            return redirect(url_for('interview'))
        else:
            return "Please enter both the job description and candidate profile.", 400

    return render_template('index.html')

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    questions = session.get('questions', [])
    question_index = session.get('question_index', 0)
    answers = session.get('answers', [])

    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        timeout = request.form.get('timeout') == 'true'

        # Save current answer
        answers.append(answer if answer else "No answer provided.")
        session['answers'] = answers

        # Move to next question
        question_index += 1
        session['question_index'] = question_index

        # If all 5 answered, generate review
        if question_index >= 5:
            reviews = []
            for i in range(5):
                review = get_review_from_gemini(questions[i], answers[i])
                reviews.append(review)
            session['reviews'] = reviews
            return redirect(url_for('review'))

        # Redirect to GET to load next question
        return redirect(url_for('interview'))

    # GET request: show current question
    if question_index < 5 and question_index < len(questions):
        question = questions[question_index]
        return render_template('interview.html', question=question)

    return redirect(url_for('review'))

@app.route('/review')
def review():
    answers = session.get('answers', [])
    questions = session.get('questions', [])
    reviews = session.get('reviews', [])

    return render_template('review.html', questions=questions, answers=answers, reviews=reviews)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
