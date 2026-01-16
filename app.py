import csv
import os
from flask import Flask, render_template, request, jsonify

# Path setup
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))

@app.route("/")
def home():
    questions_path = os.path.join(base_dir, 'questions.csv')
    questions = []
    if os.path.exists(questions_path):
        try:
            with open(questions_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 6:
                        questions.append({
                            "sawal": row[0],
                            "options": [row[1], row[2], row[3], row[4]],
                            "jawab": row[5].strip().upper()
                        })
        except Exception as e:
            print(f"CSV Error: {e}")
    
    return render_template("index.html", pittara=questions)

@app.route("/save_result", methods=["POST"])
def save_result():
    try:
        data = request.json
        name = data.get("name", "Anjan")
        score = float(data.get("score", 0))
        
        results_path = os.path.join(base_dir, 'web_results.txt')
        with open(results_path, "a") as f:
            f.write(f"{name},{score}\n")
            
        return jsonify({"status": "success", "rank": 1, "total": 1})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
