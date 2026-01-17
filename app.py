import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Hum 'cognito_v2.db' use kar rahe hain jo aapke SQL backup ko store karega
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. LATEST AI SETUP (2026 Standards) ---
# Render ke Environment Variables mein GEMINI_API_KEY hona zaroori hai
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # Latest 2026 Model: Gemini 3 Flash
    # Ye model fast hai aur educational content ke liye best hai
    ai_model = genai.GenerativeModel('models/gemini-3-flash')
else:
    ai_model = None

# --- 3. DATABASE MODELS (Aapki SQL Tables ke mutabiq) ---
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
        return jsonify({"status": "error", "message": "API Key missing in Render settings!"})
    
    data = request.json
    topic = data.get("topic", "UPSC GS")
    
    # Gemini 3 ke liye specialized prompt
    prompt = f"""
    Create 5 high-quality UPSC level MCQs on the topic: {topic}. 
    Provide them in both Hindi and English. 
    Format: Question, Options (A, B, C, D), Correct Answer, and a short Explanation.
    """
    
    try:
        # Latest generation call
        response = ai_model.generate_content(prompt)
        if response and response.text:
            return jsonify({"status": "success", "quiz": response.text})
        else:
            return jsonify({"status": "error", "message": "AI model did not return text."})
    except Exception as e:
        # Detailed error reporting
        return jsonify({"status": "error", "message": f"Gemini 3 Error: {str(e)}"})

# Subject page jahan aapka purana data dikhega
@app.route("/subject/<name>")
def subject_page(name):
    posts = Post.query.filter_by(category=name).all()
    return render_template("subject.html", subject=name, posts=posts)

if __name__ == "__main__":
    with app.app_context():
        # Ye line database file create karegi agar nahi hai toh
        db.create_all()
    app.run(debug=True)
