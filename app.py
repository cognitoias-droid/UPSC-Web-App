import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cognito_final_v100"

# --- DATABASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP (Auto-detect) ---
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = genai.GenerativeModel('gemini-pro') if api_key else None
if api_key: genai.configure(api_key=api_key)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(10), default='student')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcategories = db.relationship('SubCategory', backref='parent_cat', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer)
    text_en = db.Column(db.Text); text_hi = db.Column(db.Text)
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text); opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct_ans = db.Column(db.String(1)); explanation = db.Column(db.Text)

# --- ROUTES ---

@app.route("/system_init")
def system_init():
    db.drop_all()
    db.create_all()
    admin = User(username='admin', password=generate_password_hash('cognito123'), role='admin')
    db.session.add(admin)
    db.session.commit()
    return "SUCCESS: Sabkuch reset ho gaya hai. Login: admin / cognito123"

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_subcategory", methods=["POST"])
def add_subcategory():
    name = request.form.get("subcat_name")
    parent_id = request.form.get("parent_id")
    if name and parent_id:
        db.session.add(SubCategory(name=name, category_id=parent_id))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/api/ai_assist", methods=["POST"])
def ai_assist():
    try:
        topic = request.json.get("topic")
        prompt = (f"Create 1 UPSC MCQ on {topic}. Return ONLY raw JSON: "
                  f"{{\"q_en\":\"..\",\"q_hi\":\"..\",\"oa\":\"..\",\"ob\":\"..\",\"oc\":\"..\",\"od\":\"..\",\"ans\":\"A/B/C/D\",\"exp\":\"..\"}}")
        response = ai_model.generate_content(prompt)
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return jsonify(json.loads(clean_json))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", categories=Category.query.all())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id; session['role'] = u.role
            return redirect(url_for('admin_dashboard'))
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
