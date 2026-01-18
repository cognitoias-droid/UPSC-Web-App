import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cognito_ias_2026_pro")

# --- DATABASE CONFIG (Render Persistent Disk ke liye) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_master_v15.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP (Using Render Environment Variables) ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-pro')
else:
    ai_model = None

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True) # Email or Mobile
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student') # admin/student
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
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct = db.Column(db.String(1))
    explanation = db.Column(db.Text)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    quiz = db.relationship('Quiz') # Relationship for dashboard access

# --- MIGRATION: Purana SQL Data + Admin Setup ---
@app.route("/final_migration")
def final_migration():
    db.drop_all()
    db.create_all()
    
    # 1. Admin setup
    admin_user = User(username="admin", name="Vikas Sir", 
                      password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin_user)

    # 2. SQL Student Data Automation
    old_students = [
        ('COGNITOIAS0001', 'Manas Rai', 'manas@gmail.com'),
        ('COGNITOIAS0002', 'Rupnam Rai', 'rupnam@gmail.com'),
        ('COGNITOIAS0046', 'Awanish Rai', 'awanish@gmail.com'),
        ('COGNITOIAS0047', 'Vishesh', 'vishesh@gmail.com'),
        ('COGNITOFAC0004', 'Sharif', 'sharif@gmail.com')
    ]
    for uid, name, email in old_students:
        new_s = User(username=uid, name=name, password=generate_password_hash("123456"), role='student')
        db.session.add(new_s)

    # 3. Default Categories
    for cat in ['History', 'Polity', 'Geography', 'Economics']:
        db.session.add(Category(name=cat))
        
    db.session.commit()
    return "<h1>System Ready!</h1><p>Admin Login: <b>admin / cognito123</b><br>Student Login (e.g. Manas): <b>COGNITOIAS0001 / 123456</b></p>"

# --- AI QUIZ GENERATOR ROUTE ---
@app.route("/api/generate_quiz", methods=["POST"])
def api_generate_quiz():
    if not ai_model:
        return jsonify({"error": "AI configuration missing"}), 500
    topic = request.json.get("topic")
    prompt = f"Create 1 UPSC level MCQ on {topic}. Return ONLY JSON: {{'question': '...', 'oa': '...', 'ob': '...', 'oc': '...', 'od': '...', 'ans': 'A/B/C/D', 'exp': '...'}}"
    try:
        response = ai_model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match: return jsonify(json.loads(match.group()))
        return jsonify({"error": "AI generated invalid response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- AUTH & DASHBOARD ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id
            session['role'] = u.role
            return redirect(url_for('admin_panel' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    available_quizzes = Quiz.query.all()
    user_results = Result.query.filter_by(user_id=user.id).order_by(Result.timestamp.desc()).all()
    return render_template("home.html", user=user, available_quizzes=available_quizzes, user_results=user_results)

# --- ADMIN ROUTES ---
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    if request.method == "POST":
        f = request.form
        if 'cat_name' in f: 
            db.session.add(Category(name=f['cat_name']))
        elif 'quiz_topic' in f:
            q = Quiz(topic=f['quiz_topic'], category_id=f['cat_id'], 
                     time_limit=int(f['time']), neg_marking=float(f['neg']))
            db.session.add(q)
        elif 'q_text' in f:
            qs = Question(quiz_id=f['quiz_id'], text=f['q_text'], opt_a=f['oa'], opt_b=f['ob'], 
                          opt_c=f['oc'], opt_d=f['od'], correct=f['ans'], explanation=f['exp'])
            db.session.add(qs)
        db.session.commit()
    return render_template("admin.html", students=User.query.filter_by(role='student').all(),
                           categories=Category.query.all(), quizzes=Quiz.query.all())

# --- TEST INTERFACE & RESULTS ---
@app.route("/take_test/<int:quiz_id>")
def take_test(quiz_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = [{
        "id": q.id, "question": q.text, "options": [q.opt_a, q.opt_b, q.opt_c, q.opt_d],
        "correct": q.correct, "explanation": q.explanation
    } for q in quiz.questions]
    return render_template("test_interface.html", quiz=quiz, questions=questions)

@app.route("/submit_score", methods=["POST"])
def submit_score():
    if 'user_id' not in session: return jsonify({"status": "error"}), 403
    data = request.json
    res = Result(user_id=session['user_id'], quiz_id=data['quiz_id'], score=float(data['score']))
    db.session.add(res)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/rankings/<int:quiz_id>")
def rankings(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    results = Result.query.filter_by(quiz_id=quiz_id).order_by(Result.score.desc()).all()
    return render_template("rankings.html", quiz=quiz, results=results)

if __name__ == "__main__":
    app.run(debug=True)
