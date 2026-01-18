import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cognito_ias_master_2026")

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v35_master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = genai.GenerativeModel('gemini-pro') if api_key else None
if api_key: genai.configure(api_key=api_key)

# --- MODELS (Fulfilling WRD 3.2, 4.1, 4.2) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')
    results = db.relationship('Result', backref='student', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcategories = db.relationship('SubCategory', backref='parent_cat', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    tests = db.relationship('Test', backref='subcat_parent', lazy=True)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    test_type = db.Column(db.String(20)) # 'Practice' or 'Exam'
    time_limit = db.Column(db.Integer, default=60)
    neg_marking = db.Column(db.Float, default=0.33)
    questions = db.relationship('Question', backref='test_parent', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    text_en = db.Column(db.Text); text_hi = db.Column(db.Text)
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct_ans = db.Column(db.String(1))
    explanation = db.Column(db.Text)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- MIGRATION & SYSTEM INIT (Zaruri Route) ---

@app.route("/system_migration_init")
def system_migration_init():
    try:
        db.drop_all()
        db.create_all()
        
        # Admin setup
        admin = User(username="admin", name="Vikas Sir", 
                     password=generate_password_hash("cognito123"), role="admin")
        db.session.add(admin)
        
        # Student Migration from SQL logic
        students = [('COGNITOIAS0001', 'Manas Rai'), ('COGNITOIAS0046', 'Awanish Rai')]
        for uid, name in students:
            db.session.add(User(username=uid, name=name, 
                                password=generate_password_hash("123456"), role='student'))
        
        db.session.commit()
        return "SUCCESS: Database Created & Admin/Students Loaded."
    except Exception as e:
        return f"Error: {str(e)}"

# --- AUTH & ADMIN ROUTES ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id; session['role'] = u.role
            return redirect(url_for('admin_dashboard' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/admin")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", 
                           categories=Category.query.all(), 
                           students=User.query.filter_by(role='student').all(),
                           tests=Test.query.all())

@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    return "<h1>Student Home Coming Soon</h1><p>Admin panel functional hai.</p>"

if __name__ == "__main__":
    app.run(debug=True)
