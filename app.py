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
# Agar Render par disk use kar rahe hain toh path badal sakte hain, varna ye default hai
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

# --- MIGRATION: Purana SQL Data + Admin Setup ---
@app.route("/final_migration")
def final_migration():
    db.drop_all()
    db.create_all()
    
    # 1. Admin setup
    admin_user = User(username="admin", name="Vikas Sir", 
                      password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin_user)

    # 2. SQL Student Data Automation (Aapki SQL file se extract kiya gaya)
    old_students = [
        ('COGNITOIAS0001', 'Manas Rai', 'manas@gmail.com'),
        ('COGNITOIAS0002', 'Rupnam Rai', 'rupnam@gmail.com'),
        ('COGNITOIAS0046', 'Awanish Rai', 'awanish@gmail.com'),
        ('COGNITOIAS0047', 'Vishesh', 'vishesh@gmail.com'),
        ('COGNITOFAC0004', 'Sharif', 'sharif@gmail.com')
    ]
    for uid, name, email in old_students:
        # Student login ke liye default password '123456'
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
        return jsonify({"error": "AI configuration missing on Render"}), 500
    
    topic = request.json.get("topic")
    prompt = f"Create 1 UPSC level MCQ on {topic}. Return ONLY JSON: {{'question': '...', 'oa': '...', 'ob': '...', 'oc': '...', 'od': '...', 'ans': 'A/B/C/D', 'exp': '...'}}"
    
    try:
        response = ai_model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return jsonify(json.loads(match.group()))
        return jsonify({"error": "AI generated invalid response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- LOGIN & DASHBOARD ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id
            session['role'] = u.role
            return redirect(url_for('admin_panel' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", 
                           students=User.query.filter_by(role='student').all(),
                           categories=Category.query.all(),
                           quizzes=Quiz.query.all())

@app.route("/")
def home():
    return render_template("index.html", categories=Category.query.all())

if __name__ == "__main__":
    app.run(debug=True)
