import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cognito_ias_v1"

# Database Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cognito_basic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models (Database Structure)
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Ek category ke andar kai subcategories ho sakti hain
    subcats = db.relationship('SubCategory', backref='parent', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

# Routes
@app.route("/system_init")
def system_init():
    db.create_all()
    return "SUCCESS: Database taiyar hai! Ab /admin par jayein."

@app.route("/")
def home():
    # Home page par saari categories dikhana
    all_categories = Category.query.all()
    return render_template("home.html", categories=all_categories)

@app.route("/admin")
def admin_dashboard():
    all_categories = Category.query.all()
    return render_template("admin.html", categories=all_categories)

@app.route("/admin/add_category", methods=["POST"])
def add_category():
    name = request.form.get("cat_name")
    if name:
        new_cat = Category(name=name)
        db.session.add(new_cat)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_subcategory", methods=["POST"])
def add_subcategory():
    name = request.form.get("sub_name")
    parent_id = request.form.get("parent_id")
    if name and parent_id:
        new_sub = SubCategory(name=name, category_id=parent_id)
        db.session.add(new_sub)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
