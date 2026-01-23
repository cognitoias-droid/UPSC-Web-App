import os
import csv
from io import TextIOWrapper
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
import json

app = Flask(__name__)
app.secret_key = "cognito_ias_logic_master"

# --- CONFIGURATION (Buniyaad) ---
db_url = os.environ.get('DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cognito_v2.db'

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- GEMINI AI SETUP ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_best_model():
    try:
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-2.0-flash-exp']
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in priority:
            if p in available_models:
                return genai.GenerativeModel(p)
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

ai_model = get_best_model()

# --- MODELS ---
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
@app.route("/admin/upload_csv", methods=["POST"])
def upload_csv():
    file = request.files.get('csv_file')
    if not file: return "File nahi mili!", 400
    
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    for row in reader:
        new_q = Question(
            q_en=row['q_en'], q_hi=row.get('q_hi', ''),
            oa=row['oa'], ob=row['ob'], oc=row['oc'], od=row['od'],
            ans=row['ans'], exp=row.get('exp', '')
        )
        db.session.add(new_q)
    db.session.commit() # Permanent Save
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/generate_ai", methods=["POST"])
def generate_ai():
    try:
        topic = request.json.get("topic")
        prompt = f"Create 1 UPSC MCQ on {topic}. Return ONLY JSON: {{'q_en':'', 'q_hi':'', 'oa':'', 'ob':'', 'oc':'', 'od':'', 'ans':'A/B/C/D', 'exp':''}}"
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip()
        if "{" in raw_text:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            return jsonify(json.loads(raw_text[start:end]))
        return jsonify({"error": "No JSON"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/system_init")
def system_init():
    db.create_all() # Tables create karna
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
        q_en=request.form.get("q_en"), q_hi=request.form.get("q_hi"),
        oa=request.form.get("oa"), ob=request.form.get("ob"),
        oc=request.form.get("oc"), od=request.form.get("od"),
        ans=request.form.get("ans"), exp=request.form.get("exp")
    )
    db.session.add(new_q)
    db.session.commit() # Permanent Save
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))
@app.route("/test")
def take_test():
    # Hum filhaal random 5 sawal test ke liye nikaal rahe hain
    questions = Question.query.limit(5).all()
    return render_template("test.html", questions=questions)
if __name__ == "__main__":
    app.run(debug=True)
