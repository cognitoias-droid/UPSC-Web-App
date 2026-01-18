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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v30_final.db')
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
    username = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')
    results = db.relationship('Result', backref='student', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    display_order = db.Column(db.Integer, default=0)
    subcategories = db.relationship('SubCategory', backref='parent_cat', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='subcat', lazy=True)
    videos = db.relationship('Video', backref='subcat', lazy=True)
    tests = db.relationship('Test', backref='subcat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='published')

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    url = db.Column(db.String(500))

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    title = db.Column(db.String(200))
    test_type = db.Column(db.String(20)) 
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
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- ADMIN ROUTES (PHASE 2) ---

@app.route("/admin")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    cats = Category.query.all()
    return render_template("admin.html", categories=cats)

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_subcategory", methods=["POST"])
def add_subcategory():
    name = request.form.get("subcat_name")
    parent_id = request.form.get("parent_id")
    if name and parent_id:
        db.session.add(SubCategory(name=name, category_id=parent_id))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/api/ai_assist", methods=["POST"])
def ai_assist():
    if not ai_model: return jsonify({"error": "AI Offline"}), 500
    data = request.json
    topic = data.get("topic")
    task_type = data.get("type")
    
    if task_type == 'post':
        prompt = f"Write detailed UPSC study notes on: {topic}. Use HTML tags for formatting."
    else:
        prompt = f"Create 1 Bilingual UPSC MCQ on {topic}. Return JSON: {{'q_en':'..','q_hi':'..','oa':'..','ob':'..','oc':'..','od':'..','ans':'A/B/C/D','exp':'..'}}"

    response = ai_model.generate_content(prompt)
    if task_type == 'post':
        return jsonify({"result": response.text})
    else:
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return jsonify(json.loads(clean_json))

# --- SYSTEM & AUTH ---
@app.route("/system_migration_init")
def system_migration_init():
    db.drop_all(); db.create_all()
    admin = User(username="admin", name="Vikas Sir", password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin)
    db.session.commit()
    return "SUCCESS: System Reset."

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id; session['role'] = u.role
            return redirect(url_for('admin_dashboard' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    return "Student Home Under Construction"

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
