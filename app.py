import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v4.db')
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

# NAYA ROUTE: Category par click karne par uske andar ke topics dikhane ke liye
@app.route("/category/<int:cat_id>")
def view_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    return render_template("category_view.html", category=cat)

# NAYA ROUTE: Poora Note (Post) padhne ke liye
@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_view.html", post=post)

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    try:
        if request.method == "POST":
            # 1. Category add karna
            if 'cat_name' in request.form:
                name = request.form['cat_name']
                if name:
                    db.session.add(Category(name=name))
            
            # 2. Sub-Category add karna
            if 'subcat_name' in request.form:
                sub_name = request.form['subcat_name']
                parent_id = request.form['parent_id']
                if sub_name and parent_id:
                    db.session.add(SubCategory(name=sub_name, category_id=parent_id))

            # 3. NAYA: Post (Notes) add karna
            if 'post_title' in request.form:
                p_title = request.form['post_title']
                p_content = request.form['post_content']
                p_sub_id = request.form['sub_id']
                if p_title and p_content and p_sub_id:
                    new_post = Post(title=p_title, content=p_content, sub_category_id=p_sub_id)
                    db.session.add(new_post)
            
            db.session.commit()
            return redirect(url_for('admin_panel'))

        categories = Category.query.all()
        # Post form ke dropdown ke liye saari subcategories
        subcategories = SubCategory.query.all() 
        return render_template("admin.html", categories=categories, subcategories=subcategories)
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

@app.route("/import_my_data")
def import_data():
    try:
        subjects = ["History", "Geography", "Polity", "Economics", "Current Affairs"]
        for sub in subjects:
            if not Category.query.filter_by(name=sub).first():
                db.session.add(Category(name=sub))
        db.session.commit()

        history = Category.query.filter_by(name="History").first()
        if history:
            sub = SubCategory.query.filter_by(name="Ancient India", category_id=history.id).first()
            if not sub:
                sub = SubCategory(name="Ancient India", category_id=history.id)
                db.session.add(sub)
                db.session.commit()
            
            p = Post(title="Indus Valley Civilization", content="Indus Valley Civilization notes by Vikas Ji.", sub_category_id=sub.id)
            db.session.add(p)
            db.session.commit()
            
        return "Mubarak ho! Purana data naye system mein shift ho gaya hai. Ab Home page check karein."
    except Exception as e:
        return f"Import Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
