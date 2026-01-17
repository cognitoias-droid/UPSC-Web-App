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

# --- AI SETUP (FORCE STABLE VERSION) ---
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    # Yahan hum version='v1' force kar rahe hain taaki beta wala error na aaye
    genai.configure(api_key=api_key, transport='rest') 
    # Hum 'gemini-1.5-flash' hi use karenge kyunki ye v1 stable mein maujood hai
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

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
        return jsonify({"status": "error", "message": "API Key missing!"})
    
    data = request.json
    topic = data.get("topic", "General Studies")
    prompt = f"Create 5 UPSC level MCQs on {topic} in Hindi/English with options and answers."
    
    try:
        # Latest 2026 way to call the model
        response = ai_model.generate_content(prompt)
        return jsonify({"status": "success", "quiz": response.text})
    except Exception as e:
        # Agar error aaye toh humein pata chalega ki ye API version hai ya permission
        return jsonify({"status": "error", "message": f"System Note: {str(e)}"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
