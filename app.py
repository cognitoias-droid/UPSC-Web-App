import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cognito_secret_key_2026" # Session secure karne ke liye

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v4.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP (AUTO-DETECT MODEL) ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            selected_model = available_models[0]
            ai_model = genai.GenerativeModel(selected_model)
            print(f"DEBUG: Successfully connected to {selected_model}")
    except Exception as e:
        print(f"DEBUG: AI Setup Error: {e}")

# --- 3. DATABASE MODELS ---

# User Table: ID/Password aur Roles ke liye
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) # Aapki generated ID
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='student') # 'admin' ya 'student'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subcategories = db.relationship('SubCategory', backref='parent_category', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    posts = db.relationship('Post', backref='sub_cat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100))
    question_data = db.Column(db.Text) 
    time_limit = db.Column(db.Integer, default=10) # Minutes mein
    neg_marking = db.Column(db.Float, default=0.33)
    num_questions = db.Column(db.Integer, default=5)

# --- 4. AUTO-TABLE CREATION ---
@app.before_request
def create_tables():
    db.create_all()

# --- 5. ROUTES ---

@app.route("/")
def home():
    categories = Category.query.all()
    return render_template("home.html", categories=categories)

# --- LOGIN/LOGOUT LOGIC ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u_id = request.form.get("username")
        pwd = request.form.get("password")
        user = User.query.filter_by(username=u_id).first()
        if user and check_password_hash(user.password, pwd):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('home'))
        return "Invalid ID or Password!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ADMIN PANEL ---
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    # Security: Sirf Admin hi dekh sake
    if session.get('role') != 'admin':
        return "Access Denied! Sirf Admin hi yahan ja sakta hai."

    try:
        if request.method == "POST":
            # 1. Study Material
            if 'post_title' in request.form:
                new_post = Post(
                    title=request.form['post_title'], 
                    content=request.form['post_content'], 
                    sub_category_id=request.form['sub_id']
                )
                db.session.add(new_post)
            
            # 2. Quiz Configuration
            if 'quiz_topic' in request.form:
                new_quiz = Quiz(
                    topic=request.form['quiz_topic'],
                    time_limit=int(request.form['t_limit']),
                    neg_marking=float(request.form['n_marking']),
                    num_questions=int(request.form['num_q'])
                )
                db.session.add(new_quiz)

            # 3. User Generation (New Student ID)
            if 'new_student_id' in request.form:
                sid = request.form['new_student_id']
                spwd = generate_password_hash(request.form['new_pwd'])
                db.session.add(User(username=sid, password=spwd, role='student'))

            db.session.commit()
            return redirect(url_for('admin_panel'))

        categories = Category.query.all()
        subcategories = SubCategory.query.all() 
        return render_template("admin.html", categories=categories, subcategories=subcategories)
    except Exception as e:
        return f"Admin Panel Error: {str(e)}"

# --- QUIZ GENERATION ---
@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    if not ai_model:
        return jsonify({"status": "error", "message": "AI System Offline."})
    
    data = request.json
    topic = data.get("topic", "UPSC GS")
    num = data.get("num", 5)
    
    prompt = f'Create {num} UPSC MCQs on {topic}. Each statement on NEW LINE. Return ONLY JSON list. Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "..."}}]'
    
    try:
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        quiz_json = json.loads(raw_text)
        return jsonify({"status": "success", "quiz": quiz_json})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# --- VIEW ROUTES ---
@app.route("/category/<int:cat_id>")
def view_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    return render_template("category_view.html", category=cat)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_view.html", post=post)

@app.route("/take_test/<int:quiz_id>")
def take_test(quiz_id):
    # Yahan humne naya test interface joda hai
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template("test_interface.html", quiz=quiz)

if __name__ == "__main__":
    app.run(debug=True)
