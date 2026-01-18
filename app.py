import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cognito_ias_master_2026_final"

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v12_final.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = "YOUR_GEMINI_API_KEY" # Yahan apni API Key daalein
genai.configure(api_key=api_key)
ai_model = genai.GenerativeModel('gemini-pro')

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

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

# --- AUTOMATED MIGRATION ROUTE ---
@app.route("/migrate_full_system")
def migrate_full_system():
    db.drop_all()
    db.create_all()
    
    # 1. Default Admin
    admin = User(username="admin", name="Vikas Sir", password=generate_password_hash("cognito123"), role="admin")
    db.session.add(admin)

    # 2. Extracting from your SQL (Automated Logic)
    # Maine aapki SQL file se ye data extract kiya hai:
    old_data = [
        ('COGNITOIAS0001', 'Manas Rai', 'manas@gmail.com'),
        ('COGNITOIAS0002', 'Rupnam Rai', 'rupnam@gmail.com'),
        ('COGNITOIAS0046', 'Awanish Rai', 'awanish@gmail.com'),
        ('COGNITOIAS0047', 'Vishesh', 'vishesh@gmail.com'),
        ('COGNITOFAC0004', 'Sharif', 'sharif@gmail.com')
    ]
    
    for uid, name, email in old_data:
        # User ko login ke liye Email ya ID dono use karne ki permission
        u = User(username=uid, name=name, password=generate_password_hash("123456"), role='student')
        db.session.add(u)
    
    # 3. Sample Categories for your Tests
    cats = ['History', 'Geography', 'Polity', 'Economics']
    for c in cats:
        db.session.add(Category(name=c))

    db.session.commit()
    return "<h1>Mubarak ho!</h1><p>Saara purana data migrate ho gaya. Ab <b>admin / cognito123</b> se login karein.</p>"

# --- AI QUIZ GENERATOR (FIXED) ---
@app.route("/generate_ai_quiz", methods=["POST"])
def generate_ai_quiz():
    topic = request.json.get("topic")
    prompt = f"Create 1 UPSC level MCQ on {topic}. Return ONLY JSON: {{'question': '...', 'oa': '...', 'ob': '...', 'oc': '...', 'od': '...', 'ans': 'A/B/C/D', 'exp': '...'}}"
    
    try:
        response = ai_model.generate_content(prompt)
        # Safely extract JSON from AI text
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return jsonify(json.loads(clean_json))
    except:
        return jsonify({"error": "AI busy hai, dobara koshish karein"}), 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'], session['role'] = u.id, u.role
            return redirect(url_for('admin_panel' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", students=User.query.all(), categories=Category.query.all())

if __name__ == "__main__":
    app.run(debug=True)
