import csv
import os
from flask import Flask, render_template, request, jsonify

# --- FIX: Python ko batana ki templates folder kahan hai ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

CSV_PATH = os.path.join(BASE_DIR, 'questions.csv')
RESULTS_PATH = os.path.join(BASE_DIR, 'web_results.txt')

def get_questions():
    questions = []
    if not os.path.exists(CSV_PATH):
        return []
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 6:
                    questions.append({
                        "sawal": row[0],
                        "options": [row[1], row[2], row[3], row[4]],
                        "jawab": row[5].strip().upper()
                    })
        return questions
    except Exception as e:
        return []

@app.route("/")
def home():
    all_data = get_questions()
    return render_template("index.html", pittara=all_data)

@app.route("/save_result", methods=["POST"])
def save_result():
    try:
        data = request.json 
        name = data.get("name", "Anjan")
        current_score = float(data.get("score", 0))
        
        with open(RESULTS_PATH, "a") as f:
            f.write(f"{name},{current_score}\n")

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
            "rank": rank,
            "total": total_participants
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
