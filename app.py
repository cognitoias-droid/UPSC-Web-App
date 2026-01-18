import os, json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cognito_ias_master_2026_final"
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024 

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v11.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key: genai.configure(api_key=api_key)
ai_model = genai.GenerativeModel('gemini-pro')

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')
    results = db.relationship('Result', backref='student', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    quizzes = db.relationship('Quiz', backref='category', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    time_limit = db.Column(db.Integer, default=60)
    neg_marking = db.Column(db.Float, default=0.33)
    questions = db.relationship('Question', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    text = db.Column(db.Text) 
    opt_a = db.Column(db.Text)
    opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text)
    opt_d = db.Column(db.Text)
    correct = db.Column(db.String(1))
    explanation = db.Column(db.Text)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.before_request
def setup(): db.create_all()

# --- NEW: AI QUIZ GENERATOR ROUTE ---
@app.route("/generate_quiz_ai", methods=["POST"])
def generate_quiz_ai():
    data = request.json
    topic = data.get("topic")
    prompt = f"Create a UPSC MCQ on {topic}. Return ONLY a JSON object with: question, oa, ob, oc, od, ans (A/B/C/D), explanation."
    try:
        response = ai_model.generate_content(prompt)
        # Cleaning AI response for JSON
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(raw_text))
    except Exception as e:
        return jsonify({"error": str(e)})

# --- FINAL MIGRATION ROUTE (SQL AUTOMATION) ---
@app.route("/migrate_all_data")
def migrate_all_data():
    db.drop_all()
    db.create_all()
    
    # 1. Admin setup
    admin = User(username="admin", password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin)
    
    # 2. Automated Student Load (From your SQL users table)
    # Manas Rai, Awanish, etc. included
    old_users = [
        ('manas@gmail.com', 'Manas Rai'), 
        ('awanish@gmail.com', 'Awanish Rai'),
        ('COGNITOIAS0047', 'Vishesh'),
        ('rupnam@gmail.com', 'Rupnam Rai')
    ]
    for email, name in old_users:
        if not User.query.filter_by(username=email).first():
            db.session.add(User(username=email, password=generate_password_hash("123456"), role='student'))

    db.session.commit()
    return "Mubarak ho Vikas ji! Students, Admin aur AI generator ab bilkul taiyar hain."

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('admin_panel' if user.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", 
                           students=User.query.filter_by(role='student').all(),
                           quizzes=Quiz.query.all(),
                           categories=Category.query.all())

if __name__ == "__main__":
    app.run(debug=True)
