import os
import csv
import json
from io import TextIOWrapper
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "cognito_ias_logic_master"

# --- CONFIGURATION ---
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
        available_models = genai.list_models()
        usable_models = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
        priority = ['models/gemini-1.5-flash', 'models/gemini-pro', 'models/gemini-1.0-pro']
        for p in priority:
            if p in usable_models:
                return genai.GenerativeModel(p)
        return genai.GenerativeModel(usable_models[0] if usable_models else 'gemini-pro')
    except:
        return genai.GenerativeModel('gemini-pro')

ai_model = get_best_model()

# --- MODELS ---
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subcategories = db.relationship('SubCategory', backref='category', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    topics = db.relationship('Topic', backref='subcategory', lazy=True)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategory.id'))
    questions = db.relationship('Question', backref='topic', lazy=True)

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
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))

# --- ROUTES ---

@app.route("/")
def home():
    # Home page par hum categories dikhayenge taaki baccha select kar sake
    return render_template("home.html", categories=Category.query.all())

@app.route("/admin")
def admin_dashboard():
    all_qs = Question.query.order_by(Question.id.desc()).all()
    return render_template("admin.html", categories=Category.query.all(), questions=all_qs, q_count=len(all_qs))

@app.route("/admin/save_mcq", methods=["POST"])
def save_mcq():
    # Ab hum topic_id bhi save karenge
    new_q = Question(
        q_en=request.form.get("q_en"), 
        q_hi=request.form.get("q_hi"),
        oa=request.form.get("oa"), 
        ob=request.form.get("ob"),
        oc=request.form.get("oc"), 
        od=request.form.get("od"),
        ans=request.form.get("ans"), 
        exp=request.form.get("exp"),
        topic_id=request.form.get("topic_id") # Naya badlav
    )
    db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/bulk_ai", methods=["POST"])
def bulk_ai():
    try:
        topic_name = request.json.get("topic")
        count = int(request.json.get("count", 3))
        # AI se sawal mangwana
        prompt = f"Create {count} UPSC MCQs on '{topic_name}'. Return ONLY a JSON list: [{{'q_en':'', 'q_hi':'', 'oa':'', 'ob':'', 'oc':'', 'od':'', 'ans':'A/B/C/D', 'exp':''}}]"
        response = ai_model.generate_content(prompt)
        raw_text = response.text.strip().replace('```json', '').replace('```', '')
        questions_data = json.loads(raw_text)
        
        for item in questions_data:
            db.session.add(Question(
                q_en=item['q_en'], q_hi=item['q_hi'],
                oa=item['oa'], ob=item['ob'], oc=item['oc'], od=item['od'],
                ans=item['ans'], exp=item['exp']
                # Note: Bulk AI mein topic_id manually baad mein assign karna hoga ya Topic ID mangwani hogi
            ))
        db.session.commit()
        return jsonify({"message": f"Safalta! {len(questions_data)} sawal jodh diye gaye hain."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_subcats/<int:cat_id>")
def get_subcats(cat_id):
    subs = SubCategory.query.filter_by(category_id=cat_id).all()
    return jsonify([{"id": s.id, "name": s.name} for s in subs])

@app.route("/get_topics/<int:sub_id>")
def get_topics(sub_id):
    tops = Topic.query.filter_by(subcategory_id=sub_id).all()
    return jsonify([{"id": t.id, "name": t.name} for t in tops])

@app.route("/admin/add_structure", methods=["POST"])
def add_structure():
    stype = request.form.get("type")
    name = request.form.get("name")
    parent_id = request.form.get("parent_id")

    if stype == "category":
        db.session.add(Category(name=name))
    elif stype == "subcat":
        db.session.add(SubCategory(name=name, category_id=parent_id))
    elif stype == "topic":
        db.session.add(Topic(name=name, subcategory_id=parent_id))
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/system_init")
def system_init():
    db.create_all()
    return "SUCCESS: Tijori taiyar hai!"

@app.route("/test")
def take_test():
    # Filhaal hum random sawal dikha rahe hain
    questions = Question.query.limit(5).all()
    return render_template("test.html", questions=questions)

@app.route("/submit_test", methods=["POST"])
def submit_test():
    q_ids = request.form.getlist("question_ids")
    score = 0
    results_summary = []
    for q_id in q_ids:
        question = Question.query.get(int(q_id))
        user_ans = request.form.get(f"ans_{q_id}")
        is_correct = (user_ans == question.ans)
        if is_correct: score += 1
        results_summary.append({"question": question, "user_ans": user_ans, "is_correct": is_correct})
    return render_template("result.html", score=score, total=len(q_ids), results=results_summary)
@app.route("/test/topic/<int:topic_id>")
def test_by_topic(topic_id):
    # Sirf us specific topic ke sawal nikalna
    questions = Question.query.filter_by(topic_id=topic_id).all()
    if not questions:
        return "Is topic mein abhi koi sawal nahi hain. Admin se sampark karein!"
    return render_template("test.html", questions=questions)

if __name__ == "__main__":
    app.run(debug=True)
