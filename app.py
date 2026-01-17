import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP (AUTO-DETECT MODEL) ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Hum saare models ki list nikalenge aur pehla 'generateContent' wala model pakad lenge
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            # Aksar 'models/gemini-1.5-flash' ya 'models/gemini-pro' pehla hota hai
            selected_model = available_models[0]
            ai_model = genai.GenerativeModel(selected_model)
            print(f"DEBUG: Selected Model is {selected_model}")
    except Exception as e:
        print(f"DEBUG: AI Setup Error: {e}")

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    category = db.Column(db.String(50))

# --- ROUTES ---
@app.route("/")
def home():
    categories = ['History', 'Geography', 'Polity', 'Economics', 'Current Affairs']
    return render_template("home.html", categories=categories)

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    if not ai_model:
        return jsonify({"status": "error", "message": "AI Model detect nahi ho paya. API Key check karein."})
    
    data = request.json
    topic = data.get("topic", "UPSC GS")
    prompt = f"Create 5 UPSC level MCQs on {topic} in Hindi/English with options and answers."
    
    try:
        response = ai_model.generate_content(prompt)
        return jsonify({"status": "success", "quiz": response.text})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Run-time Error: {str(e)}"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
