import csv
import os
from flask import Flask, render_template, request, jsonify

# Render/Linux ke liye path fix
current_dir = os.path.dirname(os.path.abspath(__file__))
# Hum Flask ko zor de kar bata rahe hain ki 'templates' folder kahan hai
app = Flask(__name__, template_folder=os.path.join(current_dir, 'templates'))

def get_questions():
    questions = []
    path = os.path.join(current_dir, "questions.csv")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
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
        print(f"Error: {e}")
        return []

@app.route("/")
def home():
    all_data = get_questions()
    # Yahan error aata hai agar templates/index.html nahi milti
    return render_template("index.html", pittara=all_data)

@app.route("/save_result", methods=["POST"])
def save_result():
    try:
        data = request.json 
        name = data.get("name", "Anjan")
        score = float(data.get("score", 0))
        path_txt = os.path.join(current_dir, "web_results.txt")
        
        with open(path_txt, "a") as f:
            f.write(f"{name},{score}\n")

        all_scores = []
        if os.path.exists(path_txt):
            with open(path_txt, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        all_scores.append(float(parts[1]))
        
        all_scores.sort(reverse=True)
        rank = all_scores.index(score) + 1
        return jsonify({"status": "success", "rank": rank, "total": len(all_scores)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
