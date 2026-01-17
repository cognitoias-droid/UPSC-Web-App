import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- DATABASE SETUP ---
# Abhi ke liye hum SQLite use karenge jo aapki SQL file se data uthayega
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_CONNECTION_RECYCLE'] = 30
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_v2.db')
db = SQLAlchemy(app)

# --- MODELS (Aapki SQL tables ke hisaab se) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50)) # History, Geography etc.

# --- ROUTES ---
@app.route("/")
def home():
    # Hum categories ke hisaab se data filter karenge
    categories = ['History', 'Geography', 'Polity', 'Economics', 'Current Affairs']
    return render_template("home.html", categories=categories)

@app.route("/subject/<name>")
def subject_page(name):
    # Us subject ki posts aur quizzes yahan dikhengi
    posts = Post.query.filter_by(category=name).all()
    return render_template("subject.html", subject=name, posts=posts)

if __name__ == "__main__":
    app.run(debug=True)
