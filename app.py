import csv
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- ZAROORI: FILE PATH KO DYNAMIC BANANA ---
# Yeh line apne aap dhoond legi ki file kahan rakhi hai
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'questions.csv')
RESULTS_PATH = os.path.join(BASE_DIR, 'web_results.txt')

# --- 1. CSV SE SAWAL UTHANE KA LOGIC ---
def get_questions():
    questions = []
    # Ab hum dynamic CSV_PATH use karenge
    if not os.path.exists(CSV_PATH):
        print(f"❌ File nahi mili: {CSV_PATH}")
        return []
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None) # Pehli row skip
            for row in reader:
                if len(row) >= 6:
                    questions.append({
                        "sawal": row[0],
                        "options": [row[1], row[2], row[3], row[4]],
                        "jawab": row[5].strip().upper()
                    })
        return questions
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return []

# --- 2. HOME PAGE ROUTE ---
@app.route("/")
def home():
    all_data = get_questions()
    return render_template("index.html", pittara=all_data)

# --- 3. RESULT SAVE AUR RANK CALCULATE KARNE KA ROUTE ---
@app.route("/save_result", methods=["POST"])
def save_result():
    try:
        data = request.json 
        name = data.get("name", "Anjan")
        current_score = float(data.get("score", 0))
        
        # A. Result save karein (Dynamic path use karke)
        with open(RESULTS_PATH, "a") as f:
            f.write(f"{name},{current_score}\n")

        # B. RANK LOGIC
        all_scores = []
        if os.path.exists(RESULTS_PATH):
            with open(RESULTS_PATH, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        try:
                            all_scores.append(float(parts[1]))
                        except:
                            continue
        
        all_scores.sort(reverse=True)
        rank = all_scores.index(current_score) + 1
        total_participants = len(all_scores)

        return jsonify({
            "status": "success", 
            "message": "Result Save Ho Gaya!",
            "rank": rank,
            "total": total_participants
        })
    except Exception as e:
        print(f"❌ Error in save_result: {e}")
        return jsonify({"status": "error", "message": str(e)})

# --- 4. SERVER START ---
if __name__ == "__main__":
    # Local testing ke liye debug=True, Render ise apne aap handle karega
    app.run(debug=True)
