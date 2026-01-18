import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cognito_ias_2026_enterprise")

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v35_final.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = genai.GenerativeModel('gemini-pro') if api_key else None
if api_key: genai.configure(api_key=api_key)

# --- MODELS (Section 4 & 7 Requirements) ---

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

class Test(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    test_type = db.Column(db.String(20)) # 'Practice' (Instant) or 'Exam' (Full)
    time_limit = db.Column(db.Integer, default=60) # Minutes
    neg_marking = db.Column(db.Float, default=0.33)
    questions = db.relationship('Question', backref='test_parent', lazy=True)

class Question(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    text_en = db.Column(db.Text); text_hi = db.Column(db.Text)
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct_ans = db.Column(db.String(1)) # A/B/C/D
    explanation = db.Column(db.Text)

class Result(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    score = db.Column(db.Float)
    total_q = db.Column(db.Integer)
    correct = db.Column(db.Integer)
    wrong = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- ROUTES ---

@app.route("/admin/save_question", methods=["POST"])
def save_question():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    f = request.form
    new_q = Question(
        test_id=f.get('test_id'),
        text_en=f.get('q_en'), text_hi=f.get('q_hi'),
        opt_a=f.get('oa'), opt_b=f.get('ob'), opt_c=f.get('oc'), opt_d=f.get('od'),
        correct_ans=f.get('ans'), explanation=f.get('exp')
    )
    db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Student Side: Test Logic
@app.route("/take_test/<int:test_id>")
def take_test(test_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    test = Test.query.get_or_404(test_id)
    questions = Question.query.filter_by(test_id=test_id).all()
    
    # Practice mode vs Exam mode template selection
    if test.test_type == 'Practice':
        return render_template("quiz_practice.html", test=test, questions=questions)
    return render_template("test_exam.html", test=test, questions=questions)

# Result Submission & Analytics
@app.route("/api/submit_test", methods=["POST"])
def submit_test():
    data = request.json
    # Score calculation logic with negative marking
    res = Result(
        user_id=session['user_id'],
        test_id=data['test_id'],
        score=data['score'],
        total_q=data['total'],
        correct=data['correct'],
        wrong=data['wrong']
    )
    db.session.add(res)
    db.session.commit()
    return jsonify({"status": "success", "result_id": res.id})

# Dashboard Analytics
@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    history = Result.query.filter_by(user_id=user.id).order_by(Result.timestamp.desc()).all()
    return render_template("home.html", user=user, history=history, categories=Category.query.all())

# AI Assist Logic
@app.route("/api/ai_assist", methods=["POST"])
def ai_assist():
    if not ai_model: return jsonify({"error": "AI Config Missing"}), 500
    topic = request.json.get("topic")
    prompt = f"Create 1 Bilingual UPSC MCQ on {topic}. Return JSON: {{'q_en':'..','q_hi':'..','oa':'..','ob':'..','oc':'..','od':'..','ans':'A/B/C/D','exp':'..'}}"
    response = ai_model.generate_content(prompt)
    data = re.search(r'\{.*\}', response.text, re.DOTALL).group()
    return jsonify(json.loads(data))

@app.route("/admin")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", 
                           categories=Category.query.all(), 
                           tests=Test.query.all(),
                           students=User.query.filter_by(role='student').all())

if __name__ == "__main__":
    app.run(debug=True)
