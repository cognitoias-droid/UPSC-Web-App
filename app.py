import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
import json

app = Flask(__name__)
app.secret_key = "cognito_ias_logic_master"

# --- CONFIGURATION (Buniyaad) ---
db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Render ki 'postgres://' ko 'postgresql://' mein badalna
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cognito_v2.db'

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- GEMINI AI SETUP (Quota Friendly Logic) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_best_model():
    try:
        # Priority: 1.5-flash ko pehle rakha hai kyunki iska free quota sabse zyada hai
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-2.0-flash-exp']
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        for p in priority:
            if p in available_models:
                print(f"DEBUG: Using Model -> {p}")
                return genai.GenerativeModel(p)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Model selection error: {e}")
        return genai.GenerativeModel('gemini-1.5-flash')

ai_model = get_best_model()

# --- AI GENERATION ROUTE ---
@app.route("/admin/generate_ai", methods=["POST"])
def generate_ai():
    try:
        topic = request.json.get("topic")
        
        prompt = f"""
        Task: Create 1 UPSC Level MCQ on {topic}. 
        Format: Return ONLY a valid JSON object. No extra text, no markdown.
        Structure: {{
            "q_en": "Question in English",
            "q_hi": "Question in Hindi",
            "oa": "Option A",
            "ob": "Option B",
            "oc": "Option C",
            "od": "Option D",
            "ans": "Correct Letter A/B/C/D",
            "exp": "Detailed explanation in Hindi"
        }}
        """
        
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Safe JSON Extraction logic
        if "{" in raw_text:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            data = json.loads(raw_text[start:end])
            return jsonify(data)
        else:
            return jsonify({"error": "AI response was not in JSON format"}), 500
            
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        # User ko quota error ki jaankari dena
        if "429" in str(e):
            return jsonify({"error": "AI Quota Full: Please try again in 1 minute."}), 429
        return jsonify({"error": str(e)}), 500

# --- MODELS (Almariyan) ---
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcats = db.relationship('SubCategory', backref='parent', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q_en = db.Column(db.Text)
    q_hi = db.Column(db.Text)
    oa = db.Column(db.String(200))
    ob = db.Column(db.String(200))
    oc = db.Column(db.String(200))
    od = db.Column(db.String(200))
    ans = db.Column(db.String(5))
    exp = db.Column(db.Text)

# --- ROUTES ---
@app.route("/system_init")
def system_init():
    db.create_all() # PostgreSQL tables setup
    return "SUCCESS: Tijori taiyar hai!"

@app.route("/")
def home():
    return render_template("home.html", questions=Question.query.all(), categories=Category.query.all())

@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html", categories=Category.query.all())

@app.route("/admin/save_mcq", methods=["POST"])
def save_mcq():
    new_q = Question(
        q_en=request.form.get("q_en"),
        q_hi=request.form.get("q_hi"),
        oa=request.form.get("oa"),
        ob=request.form.get("ob"),
        oc=request.form.get("oc"),
        od=request.form.get("od"),
        ans=request.form.get("ans"),
        exp=request.form.get("exp")
    )
    db.session.add(new_q)
    db.session.commit() # Permanent save
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
