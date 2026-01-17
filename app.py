import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP (GEMINI 1.5 FLASH) ---
# Render ke 'Environment' tab mein GEMINI_API_KEY zaroor check karein
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # 2026 ka sabse stable model name: 'gemini-1.5-flash'
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

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

# --- 4. ROUTES ---
@app.route("/")
def home():
    categories = ['History', 'Geography', 'Polity', 'Economics', 'Current Affairs']
    return render_template("home.html", categories=categories)

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    if not ai_model:
        return jsonify({"status": "error", "message": "API Key nahi mili! Render settings check karein."})
    
    data = request.json
    topic = data.get("topic", "General Studies")
    
    # AI ko bilkul saaf instruction
    prompt = f"Write 5 UPSC level MCQs on the topic: {topic}. Provide Question, Options (A, B, C, D) and the Correct Answer for each. Keep it in Hindi and English."
    
    try:
        # Latest method for Gemini 1.5
        response = ai_model.generate_content(prompt)
        if response and response.text:
            return jsonify({"status": "success", "quiz": response.text})
        else:
            return jsonify({"status": "error", "message": "AI ne khali jawab diya."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
