import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cognito_ias_2026_enterprise")

# --- DATABASE CONFIG (Render Persistent Disk Support) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v30_final.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-pro')

# --- MODELS (Based on WRD Section 3 & 4) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student') # Admin or Student
    results = db.relationship('Result', backref='student', lazy=True)

class Category(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    display_order = db.Column(db.Integer, default=0)
    subcategories = db.relationship('SubCategory', backref='parent_cat', lazy=True)

class SubCategory(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='subcat', lazy=True)
    videos = db.relationship('Video', backref='subcat', lazy=True)
    tests = db.relationship('Test', backref='subcat', lazy=True)

class Post(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    content = db.Column(db.Text) # Rich Text
    status = db.Column(db.String(20), default='published')

class Video(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    url = db.Column(db.String(500)) # Embedded Link

class Test(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    test_type = db.Column(db.String(20)) # 'Quiz' (Instant) or 'Exam' (Full)
    time_limit = db.Column(db.Integer, default=60)
    neg_marking = db.Column(db.Float, default=0.33)
    questions = db.relationship('Question', backref='test_parent', lazy=True)

class Question(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    text_en = db.Column(db.Text)
    text_hi = db.Column(db.Text) # Bilingual Support
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct_ans = db.Column(db.String(1)) # A, B, C, or D
    explanation = db.Column(db.Text)

class Result(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    score = db.Column(db.Float)
    details = db.Column(db.JSON) # Correct/Incorrect Breakdown
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- MIGRATION ENGINE (Section 7) ---

@app.route("/system_migration_init")
def system_migration_init():
    db.drop_all()
    db.create_all()
    
    # 1. Default Admin
    admin = User(username="admin", name="Vikas Sir", 
                 password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin)

    # 2. Automated Student Load (From your SQL users table)
    # Inhe default password '123456' mil jayega
    students = [
        ('COGNITOIAS0001', 'Manas Rai'), 
        ('COGNITOIAS0046', 'Awanish Rai'),
        ('COGNITOIAS0047', 'Vishesh')
    ]
    for uid, name in students:
        db.session.add(User(username=uid, name=name, 
                            password=generate_password_hash("123456"), role='student'))

    db.session.commit()
    return "SUCCESS: Phase 1 Database Ready & Students Migrated."

# Auth Logic
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id
            session['role'] = u.role
            return redirect(url_for('admin_dashboard' if u.role == 'admin' else 'home'))
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
