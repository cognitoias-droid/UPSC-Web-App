import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. CONFIGURATION & DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SQLite database setup (Aapki SQL file se data yahan aayega)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP (Gemini) ---
# Render ki 'Environment' settings se key uthayega
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-pro')
else:
    ai_model = None

# --- 3. DATABASE MODELS (Aapki SQL tables ke mutabiq) ---
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
        return jsonify({"status": "error", "message": "API Key nahi mili. Render settings check karein."})
    
    data = request.json
    topic = data.get("topic", "UPSC General Studies")
    
    prompt = f"Create 5 tough UPSC level MCQs in Hindi and English on the topic: {topic}. Provide 4 options (A, B, C, D) and the correct answer for each."
    
    try:
        response = ai_model.generate_content(prompt)
        return jsonify({"status": "success", "quiz": response.text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Pehli baar database file banane ke liye
    app.run(debug=True)
