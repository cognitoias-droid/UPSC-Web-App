import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cognito_master_2026_final"

# --- 1. DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v4.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        ai_model = genai.GenerativeModel(models[0])
    except: pass

# --- 3. MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcategories = db.relationship('SubCategory', backref='parent_category', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='sub_cat', lazy=True)
    quizzes = db.relationship('Quiz', backref='linked_subcat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100))
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    question_data = db.Column(db.Text) 
    time_limit = db.Column(db.Integer, default=10)
    neg_marking = db.Column(db.Float, default=0.33)

@app.before_request
def create_tables(): db.create_all()

# --- 4. NEW AI FEATURES ---
@app.route("/ai_write", methods=["POST"])
def ai_write():
    data = request.json
    prompt = f"Write detailed UPSC notes on '{data['topic']}' in Hindi and English mix. Use HTML <h2>, <p>, <ul> tags."
    if ai_model:
        response = ai_model.generate_content(prompt)
        return jsonify({"content": response.text})
    return jsonify({"content": "AI not connected."})

@app.route("/ai_create_test", methods=["POST"])
def ai_create_test():
    data = request.json
    prompt = f"Create 5 UPSC MCQs from this content: {data['content']}. Return ONLY a JSON list: [{{'question':'','options':['','','',''],'answer':'A','explanation':''}}]"
    if ai_model:
        response = ai_model.generate_content(prompt)
        raw = response.text.replace('```json', '').replace('```', '').strip()
        return jsonify({"quiz": json.loads(raw)})
    return jsonify({"quiz": []})

# --- 5. ROUTES ---
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    if request.method == "POST":
        # Add Student logic
        if 'new_student_id' in request.form:
            db.session.add(User(username=request.form['new_student_id'], password=generate_password_hash(request.form['new_pwd'])))
        # Manual Question logic
        if 'q_text' in request.form:
            sub_id = request.form['quiz_sub_id']
            q_data = {"question": request.form['q_text'], "options": [request.form['opt_a'], request.form['opt_b'], request.form['opt_c'], request.form['opt_d']], "answer": request.form['q_ans'].upper()}
            quiz = Quiz.query.filter_by(sub_category_id=sub_id).first()
            if quiz:
                qs = json.loads(quiz.question_data); qs.append(q_data); quiz.question_data = json.dumps(qs)
            else:
                db.session.add(Quiz(topic="Topic Test", sub_category_id=sub_id, question_data=json.dumps([q_data])))
        db.session.commit()
    return render_template("admin.html", categories=Category.query.all(), subcategories=SubCategory.query.all(), students=User.query.filter_by(role='student').all(), quizzes=Quiz.query.all())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'], session['role'], session['username'] = user.id, user.role, user.username
            return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/")
def home(): return render_template("home.html", categories=Category.query.all())

@app.route("/take_test/<int:quiz_id>")
def take_test(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template("test_interface.html", quiz=quiz, questions=json.loads(quiz.question_data))

@app.route("/create_my_admin")
def create_my_admin():
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password=generate_password_hash("cognito123"), role="admin"))
        db.session.commit()
    return "Admin ready! ID: admin, PWD: cognito123"
    @app.route("/sync_old_students")
def sync_old_students():
    # Purane database se nikala gaya data (Aapki SQL file ke mutabik)
    # Maine top students ki list yahan di hai, baaki aap isi format mein jodd sakte hain
    old_data = [
        ('COGNITOIAS0046', 'awanish rai'),
        ('COGNITOIAS0047', 'Vishesh'),
        ('COGNITOIAS0030', 'Aman Deep'),
        ('COGNITOIAS0035', 'Sushmita'),
        # ... isi tarah baaki IDs
    ]
    
    count = 0
    from werkzeug.security import generate_password_hash
    
    for username, name in old_data:
        # Check karein agar student pehle se toh nahi hai
        exists = User.query.filter_by(username=username).first()
        if not exists:
            # Purana password hashed tha, isliye temporary password '123456' set kar rahe hain
            # Bache login karke ise baad mein badal sakte hain
            hashed_pwd = generate_password_hash("123456")
            new_student = User(username=username, password=hashed_pwd, role='student')
            db.session.add(new_student)
            count += 1
            
    db.session.commit()
    return f"Mubarak ho! {count} purane students naye system mein successfully merge ho gaye hain. Unka temporary password '123456' hai."

if __name__ == "__main__": app.run(debug=True)
