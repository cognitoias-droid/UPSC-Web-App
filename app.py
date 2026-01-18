import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Database ka naam thoda badal dete hain taaki naya system fresh start kare
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v3.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# --- 3. DYNAMIC DATABASE MODELS ---
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subcategories = db.relationship('SubCategory', backref='parent_category', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    posts = db.relationship('Post', backref='sub_cat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100))
    question_data = db.Column(db.Text) 

# --- 4. ROUTES ---

@app.route("/")
def home():
    try:
        categories = Category.query.all()
        return render_template("home.html", categories=categories)
    except Exception as e:
        # Agar table nahi mili toh system ko batayein ki database create karein
        return f"Database Initialization Pending. Please refresh this page. Error: {str(e)}"

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    try:
        if request.method == "POST":
            if 'cat_name' in request.form:
                name = request.form['cat_name']
                if name:
                    new_cat = Category(name=name)
                    db.session.add(new_cat)
            
            if 'subcat_name' in request.form:
                sub_name = request.form['subcat_name']
                parent_id = request.form['parent_id']
                if sub_name and parent_id:
                    new_sub = SubCategory(name=sub_name, category_id=parent_id)
                    db.session.add(new_sub)
            
            db.session.commit()
            return redirect(url_for('admin_panel'))

        categories = Category.query.all()
        return render_template("admin.html", categories=categories)
    except Exception as e:
        return f"Admin Panel Error: {str(e)}"

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    if not ai_model:
        return jsonify({"status": "error", "message": "API Key missing!"})
    
    data = request.json
    topic = data.get("topic", "UPSC")
    prompt = f'Create 5 UPSC MCQs on {topic}. Return ONLY a JSON list. Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "..."}}]'
    
    try:
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip().replace('```json', '').replace('```', '')
        quiz_json = json.loads(raw_text)
        
        new_quiz = Quiz(topic=topic, question_data=raw_text)
        db.session.add(new_quiz)
        db.session.commit()
        
        return jsonify({"status": "success", "quiz": quiz_json})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    with app.app_context():
        # Ye line naya database banayegi
        db.create_all()
    app.run(debug=True)
