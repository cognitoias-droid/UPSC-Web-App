import os
import csv
import google.generativeai as genai  # Sabse upar imports mein jodein
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. CONFIGURATION & DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP (Gemini) ---
# Yahan apni API Key dalein ya Render ki Environment Variable use karein
genai.configure(api_key="YOUR_GEMINI_API_KEY") 
ai_model = genai.GenerativeModel('gemini-pro')

# --- 3. DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))

# --- 4. ROUTES (Raste) ---

@app.route("/")
def home():
    categories = ['History', 'Geography', 'Polity', 'Economics', 'Current Affairs']
    return render_template("home.html", categories=categories)

# AI QUIZ GENERATOR ROUTE (Ise yahan jodein)
@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    topic = data.get("topic", "UPSC General Studies")
    
    # AI ko instruction dena
    prompt = f"Create 5 UPSC level MCQs in Hindi/English on {topic} with options A, B, C, D and the correct answer."
    
    try:
        response = ai_model.generate_content(prompt)
        # Abhi ke liye hum sirf AI ka text dikhayenge
        return jsonify({"status": "success", "quiz": response.text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/subject/<name>")
def subject_page(name):
    posts = Post.query.filter_by(category=name).all()
    return render_template("subject.html", subject=name, posts=posts)

if __name__ == "__main__":
    # Database table banane ke liye (Sirf pehli baar)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
