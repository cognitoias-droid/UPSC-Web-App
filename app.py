import os, json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cognito_ias_master_2026"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# --- DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v5.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None
if api_key:
    genai.configure(api_key=api_key)
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

# --- ADMIN ROUTES ---
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
    
    return render_template("admin.html", categories=Category.query.all(), subcategories=SubCategory.query.all(), quizzes=Quiz.query.all(), students=User.query.filter_by(role='student').all())

# --- AI ROUTES ---
@app.route("/ai_action", methods=["POST"])
def ai_action():
    data = request.json
    prompt = data.get("prompt")
    if ai_model:
        response = ai_model.generate_content(prompt)
        return jsonify({"result": response.text})
    return jsonify({"result": "AI Offline"})

# --- MIGRATION ROUTE ---
@app.route("/migrate_all")
def migrate_all():
    # Purane database se students migrate karna
    count = 0
    old_students = [('COGNITOIAS0046', 'awanish rai'), ('COGNITOIAS0047', 'Vishesh')] # Yahan list extend kar sakte hain
    for uid, name in old_students:
        if not User.query.filter_by(username=uid).first():
            db.session.add(User(username=uid, password=generate_password_hash("123456"), role="student"))
            count += 1
    db.session.commit()
    return f"{count} Students Migrated!"
    
@app.route("/submit_score", methods=["POST"])
def submit_score():
    data = request.json
    if 'user_id' in session:
        new_result = Result(
            user_id=session['user_id'],
            quiz_id=data['quiz_id'],
            score=data['score']
        )
        db.session.add(new_result)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

if __name__ == "__main__": app.run(debug=True)
