import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Hum v4 hi rakhenge taaki aapka mehnat se dala gaya data delete na ho
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v4.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. AI SETUP (SMART AUTO-DETECT) ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Aapka purana pasandida logic: Available models ki list nikalna
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            # Sabse naya model auto-select hoga
            selected_model = available_models[0]
            ai_model = genai.GenerativeModel(selected_model)
            print(f"DEBUG: Successfully connected to {selected_model}")
    except Exception as e:
        print(f"DEBUG: AI Setup Error: {e}")

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

# --- 4. AUTO-TABLE CREATION ---
@app.before_request
def create_tables():
    db.create_all()

# --- 5. ROUTES ---

@app.route("/")
def home():
    try:
        categories = Category.query.all()
        return render_template("home.html", categories=categories)
    except Exception as e:
        return f"Home Page Error: {str(e)}"

@app.route("/category/<int:cat_id>")
def view_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    return render_template("category_view.html", category=cat)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_view.html", post=post)

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    try:
        if request.method == "POST":
            if 'cat_name' in request.form:
                db.session.add(Category(name=request.form['cat_name']))
            
            if 'subcat_name' in request.form:
                db.session.add(SubCategory(name=request.form['subcat_name'], category_id=request.form['parent_id']))

            if 'post_title' in request.form:
                new_post = Post(
                    title=request.form['post_title'], 
                    content=request.form['post_content'], 
                    sub_category_id=request.form['sub_id']
                )
                db.session.add(new_post)
            
            db.session.commit()
            return redirect(url_for('admin_panel'))

        categories = Category.query.all()
        subcategories = SubCategory.query.all() 
        return render_template("admin.html", categories=categories, subcategories=subcategories)
    except Exception as e:
        return f"Admin Panel Error: {str(e)}"

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    if not ai_model:
        return jsonify({"status": "error", "message": "AI System taiyar nahi hai. API Key check karein."})
    
    data = request.json
    topic = data.get("topic", "UPSC GS")
    
    # Hum AI se JSON mangenge taaki aapka interactive quiz (click wala) chalta rahe
    prompt = f'Create 5 UPSC level MCQs on {topic}. Return ONLY a JSON list. Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "..."}}]'
    
    try:
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean JSON markdown if AI adds it
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        quiz_json = json.loads(raw_text)
        return jsonify({"status": "success", "quiz": quiz_json})
    except Exception as e:
        return jsonify({"status": "error", "message": f"AI Generation failed: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
