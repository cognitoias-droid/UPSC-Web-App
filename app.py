import os, json, re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cognito_final_master_2026")

# --- DATABASE SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v70.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI MODEL INITIALIZATION ---
# Is logic se AI model khud ko environment se connect kar lega
api_key = os.environ.get("GEMINI_API_KEY")
ai_model = None
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-pro')

# --- MODELS (As per WRD Requirements) ---
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

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    subcat_id = db.Column(db.Integer)
    test_type = db.Column(db.String(20)) # Practice / Exam
    questions = db.relationship('Question', backref='test_parent', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))
    text_en = db.Column(db.Text); text_hi = db.Column(db.Text)
    opt_a = db.Column(db.Text); opt_b = db.Column(db.Text)
    opt_c = db.Column(db.Text); opt_d = db.Column(db.Text)
    correct_ans = db.Column(db.String(1))
    explanation = db.Column(db.Text)

# --- ROUTES ---

@app.route("/system_init")
def system_init():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('cognito123'), role='admin'))
        db.session.commit()
    return "SUCCESS: Platform Ready. Login: admin/cognito123"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id; session['role'] = u.role
            return redirect(url_for('admin_dashboard' if u.role == 'admin' else 'home'))
    return render_template("login.html")

@app.route("/admin")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template("admin.html", categories=Category.query.all(), tests=Test.query.all())

# Fixed Routes to prevent "Not Found"
@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/save_question", methods=["POST"])
def save_question():
    f = request.form
    new_q = Question(
        test_id=f.get('test_id'), text_en=f.get('q_en'), text_hi=f.get('q_hi'),
        opt_a=f.get('oa'), opt_b=f.get('ob'), opt_c=f.get('oc'), opt_d=f.get('od'),
        correct_ans=f.get('ans'), explanation=f.get('exp')
    )
    db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- AI ASSIST LOGIC (Fixed & Robust) ---
@app.route("/api/ai_assist", methods=["POST"])
def ai_assist():
    try:
        if not ai_model: return jsonify({"error": "API Key Missing"}), 500
        data = request.json
        topic = data.get("topic")
        task = data.get("type")

        if task == 'post':
            prompt = f"Write detailed UPSC study notes on {topic} in Bilingual (Hindi/English). Use HTML tags."
            response = ai_model.generate_content(prompt)
            return jsonify({"result": response.text})
        else:
            # Sakht instruction taaki AI sirf JSON de
            prompt = (f"Create 1 UPSC MCQ on {topic}. Return ONLY a raw JSON object. "
                      f"Format: {{\"q_en\":\"..\",\"q_hi\":\"..\",\"oa\":\"..\",\"ob\":\"..\",\"oc\":\"..\",\"od\":\"..\",\"ans\":\"A/B/C/D\",\"exp\":\"..\"}}")
            response = ai_model.generate_content(prompt)
            
            # Regex se sirf JSON nikalna (Puraani galti sudhaar di gayi hai)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return jsonify(json.loads(json_match.group()))
            else:
                return jsonify({"error": "AI response format invalid"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template("home.html", categories=Category.query.all())

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
