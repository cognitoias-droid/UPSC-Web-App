import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "cognito_ias_logic_master"

# --- CONFIGURATION (Buniyaad) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Logic: External Database (PostgreSQL) ya SQLite
# Pehle check karein ki kya Render ne DATABASE_URL di hai
# --- CONFIGURATION (Sahi Logic) ---
db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Render ki 'postgres://' ko 'postgresql://' mein badalna zaruri hai
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    # Local testing ke liye (Render par ye line nahi chalni chahiye)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cognito_v2.db'

# Ye line bohot zaruri hai Render ke liye
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

# SABSE ZARURI: db ko define karna (Iske bina Error aati hai)
db = SQLAlchemy(app)

# --- MODELS (Almariyan/Registers) ---

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

# --- ROUTES (Raste aur Logic) ---

@app.route("/system_init")
def system_init():
    # Nayi Tijori (PostgreSQL) mein tables banane ke liye
    db.create_all() 
    return "SUCCESS: Tijori taiyar hai! Ab data safe rahega."

@app.route("/")
def home():
    sari_questions = Question.query.all()
    sari_categories = Category.query.all()
    return render_template("home.html", questions=sari_questions, categories=sari_categories)

@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html", categories=Category.query.all())

@app.route("/admin/save_mcq", methods=["POST"])
def save_mcq():
    en = request.form.get("q_en")
    hi = request.form.get("q_hi")
    a = request.form.get("oa")
    b = request.form.get("ob")
    c = request.form.get("oc")
    d = request.form.get("od")
    correct = request.form.get("ans")
    explanation = request.form.get("exp")

    if en:
        new_q = Question(q_en=en, q_hi=hi, oa=a, ob=b, oc=c, od=d, ans=correct, exp=explanation)
        db.session.add(new_q)
        db.session.commit()
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
