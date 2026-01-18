import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "cognito_ias_v2_fixed"

# Database Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_basic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# AI Setup (Gemini)
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-pro')

# Models
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcats = db.relationship('SubCategory', backref='parent', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='subcat', lazy=True)
    videos = db.relationship('Video', backref='subcat', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    url = db.Column(db.String(500))
    subcat_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))

# Routes
@app.route("/system_init")
def system_init():
    db.create_all()
    return "SUCCESS: Phase 2 Ready!"

@app.route("/")
def home():
    return render_template("home.html", categories=Category.query.all())

@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html", categories=Category.query.all())

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_subcategory", methods=["POST"])
def add_subcategory():
    name = request.form.get("sub_name")
    pid = request.form.get("parent_id")
    if name and pid:
        db.session.add(SubCategory(name=name, category_id=pid))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_content", methods=["POST"])
def add_content():
    f = request.form
    if f.get('type') == 'post':
        db.session.add(Post(title=f.get('title'), content=f.get('content'), subcat_id=f.get('sub_id')))
    else:
        db.session.add(Video(title=f.get('title'), url=f.get('url'), subcat_id=f.get('sub_id')))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/api/ai_assist", methods=["POST"])
def ai_assist():
    if not ai_model:
        return jsonify({"error": "AI not configured"}), 500
    topic = request.json.get("topic")
    prompt = f"Write detailed UPSC study notes on {topic}. Use HTML tags. Bilingual Hindi/English."
    response = ai_model.generate_content(prompt)
    return jsonify({"result": response.text})

if __name__ == "__main__":
    app.run(debug=True)
