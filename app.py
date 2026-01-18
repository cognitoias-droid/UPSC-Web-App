import os, json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cognito_ias_master_2026_final"
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = genai.GenerativeModel('gemini-pro') if api_key else None
if api_key: genai.configure(api_key=api_key)

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
    videos = db.relationship('Video', backref='category', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200))
    description = db.Column(db.Text)
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

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    url = db.Column(db.String(500))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

@app.before_request
def create_tables(): db.create_all()

# --- LOGIN/AUTH ROUTES ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            return redirect(url_for('home'))
        return "Ghalat credentials!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- MAIN ROUTES ---
@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    categories = Category.query.all()
    return render_template("home.html", categories=categories)

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    if request.method == "POST":
        f = request.form
        if 'cat_name' in f: db.session.add(Category(name=f['cat_name']))
        elif 'quiz_topic' in f:
            q = Quiz(topic=f['quiz_topic'], description=f['quiz_desc'], category_id=f['cat_id'], 
                     time_limit=int(f['time']), neg_marking=float(f['neg']))
            db.session.add(q)
        elif 'q_text' in f:
            qs = Question(quiz_id=f['quiz_id'], text=f['q_text'], opt_a=f['oa'], opt_b=f['ob'], 
                          opt_c=f['oc'], opt_d=f['od'], correct=f['ans'], explanation=f['exp'])
            db.session.add(qs)
        elif 'video_url' in f:
            v = Video(title=f['v_title'], url=f['video_url'], category_id=f['v_cat_id'])
            db.session.add(v)
        db.session.commit()
    return render_template("admin.html", categories=Category.query.all(), quizzes=Quiz.query.all(), students=User.query.filter_by(role='student').all())

@app.route("/ai_call", methods=["POST"])
def ai_call():
    prompt = request.json.get("prompt")
    if ai_model:
        response = ai_model.generate_content(prompt)
        return jsonify({"result": response.text})
    return jsonify({"result": "AI Connection Error"})

# --- MIGRATION ROUTE ---
@app.route("/migrate_complete")
def migrate_complete():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password=generate_password_hash("cognito123"), role="admin"))

    students_list = [
        ('COGNITOIAS0001', 'Manas Rai', 'manas@gmail.com'),
        ('COGNITOIAS0046', 'Awanish Rai', 'awanish@gmail.com'),
        ('COGNITOIAS0047', 'Vishesh', 'vishesh@gmail.com')
    ]
    for uid, name, email in students_list:
        if not User.query.filter_by(username=uid).first():
            db.session.add(User(username=uid, password=generate_password_hash("123456"), role="student"))

    if not Category.query.filter_by(name="History").first():
        hist_cat = Category(name="History")
        db.session.add(hist_cat)
        db.session.flush()
        test1 = Quiz(topic="Books and Author (Modern History)", 
                     description="Complete Test on Modern History Authors",
                     category_id=hist_cat.id, time_limit=90, neg_marking=0.33)
        db.session.add(test1)
        db.session.flush()
        q1 = Question(quiz_id=test1.id, text="Which one of the following pairs is correctly matched?",
                      opt_a="Abul Kalam Azad – Hind Swaraj", opt_b="Annie Besant – New India",
                      opt_c="Bal Gangadhar Tilak – Common Weal", opt_d="Mahatma Gandhi – India Wins Freedom",
                      correct="B", explanation="Annie Besant started New India.")
        db.session.add(q1)

    db.session.commit()
    return "Mubarak ho! Sab kuch migrate ho gaya hai."

if __name__ == "__main__":
    app.run(debug=True)
