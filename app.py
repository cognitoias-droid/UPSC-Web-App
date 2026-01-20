import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "cognito_ias_logic_master"

# Database Path Logic
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS (Almariyan) ---

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcats = db.relationship('SubCategory', backref='parent', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

# NAYA LOGIC: Question ki Almari
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

# --- ROUTES (Raste) ---

@app.route("/system_init")
def system_init():
    db.create_all() # Sari almariyan ek sath banana
    return "SUCCESS: Platform Ready!"

@app.route("/")
def home():
    return render_template("home.html", categories=Category.query.all())

@app.route("/admin")
def admin_dashboard():
    # Admin page ko categories ki list chahiye dropdown ke liye
    return render_template("admin.html", categories=Category.query.all())

# Logic: MCQ Save karne ka function
@app.route("/admin/save_mcq", methods=["POST"])
def save_mcq():
    # Bridge: HTML ke 'name' se data pakadna
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

# Purane Category/Subcategory Routes
@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
