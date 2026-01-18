import os, json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cognito_ias_master_2026_final"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# --- 1. DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v5.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        ai_model = genai.GenerativeModel('gemini-pro')
    except: pass

# --- 3. DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')
    results = db.relationship('Result', backref='student', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcategories = db.relationship('SubCategory', backref='category', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='subcat', lazy=True)
    quizzes = db.relationship('Quiz', backref='subcat', lazy=True)
    videos = db.relationship('Video', backref='subcat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200))
    description = db.Column(db.Text)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
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
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

@app.before_request
def create_tables(): db.create_all()

# --- 4. ROUTES ---

@app.route("/")
def home():
    categories = Category.query.all()
    return render_template("home.html", categories=categories)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            return redirect(url_for('home'))
        return "Invalid Login!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ADMIN PANEL ---
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    if request.method == "POST":
        f = request.form
        if 'cat_name' in f: db.session.add(Category(name=f['cat_name']))
        if 'subcat_name' in f: db.session.add(SubCategory(name=f['subcat_name'], category_id=f['parent_id']))
        if 'quiz_topic' in f:
            db.session.add(Quiz(topic=f['quiz_topic'], description=f['quiz_desc'], sub_category_id=f['sub_id'], time_limit=int(f['time']), neg_marking=float(f['neg'])))
        if 'q_text' in f:
            db.session.add(Question(quiz_id=f['target_quiz'], text=f['q_text'], opt_a=f['oa'], opt_b=f['ob'], opt_c=f['oc'], opt_d=f['od'], correct=f['ans'], explanation=f['exp']))
        if 'video_title' in f:
            db.session.add(Video(title=f['video_title'], url=f['video_url'], sub_category_id=f['v_sub_id']))
        if 'post_title' in f:
            db.session.add(Post(title=f['post_title'], content=f['post_content'], sub_category_id=f['p_sub_id']))
        db.session.commit()
        return redirect(url_for('admin_panel'))
    
    return render_template("admin.html", 
                           categories=Category.query.all(), 
                           subcategories=SubCategory.query.all(), 
                           quizzes=Quiz.query.all(), 
                           students=User.query.filter_by(role='student').all())

# --- AI & TEST LOGIC ---
@app.route("/ai_action", methods=["POST"])
def ai_action():
    data = request.json
    if ai_model:
        response = ai_model.generate_content(data.get("prompt"))
        return jsonify({"result": response.text})
    return jsonify({"result": "AI Offline"})

@app.route("/take_test/<int:quiz_id>")
def take_test(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = [{
        "id": q.id, "question": q.text, 
        "options": [q.opt_a, q.opt_b, q.opt_c, q.opt_d], 
        "correct": q.correct, "explanation": q.explanation
    } for q in quiz.questions]
    return render_template("test_interface.html", quiz=quiz, questions=questions)

@app.route("/submit_score", methods=["POST"])
def submit_score():
    data = request.json
    if 'user_id' in session:
        res = Result(user_id=session['user_id'], quiz_id=data['quiz_id'], score=data['score'])
        db.session.add(res)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route("/rankings/<int:quiz_id>")
def rankings(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    results = Result.query.filter_by(quiz_id=quiz_id).order_by(Result.score.desc()).all()
    return render_template("rankings.html", quiz=quiz, results=results)

# --- MIGRATION & SETUP ---
@app.route("/create_my_admin")
def create_my_admin():
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password=generate_password_hash("cognito123"), role="admin"))
        db.session.commit()
    return "Admin Ready!"

@app.route("/migrate_all")
def migrate_all():
    # Aapke SQL file se nikale gaye top students
    old_students = [('COGNITOIAS0046', 'awanish rai'), ('COGNITOIAS0047', 'Vishesh'), ('COGNITOIAS0030', 'Aman Deep')]
    for uid, name in old_students:
        if not User.query.filter_by(username=uid).first():
            db.session.add(User(username=uid, password=generate_password_hash("123456"), role="student"))
    db.session.commit()
    return "Migration Successful!"

if __name__ == "__main__":
    app.run(debug=True)
