import csv
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- 1. CSV SE SAWAL UTHANE KA LOGIC ---
def get_questions():
    questions = []
    path = "/Users/vikaschandra/Desktop/questions.csv"
    if not os.path.exists(path):
        print(f"❌ File nahi mili: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None) # Pehli row (heading) skip karne ke liye
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
    # Dhyaan dein: HTML mein 'pittara' variable use ho raha hai
    return render_template("index.html", pittara=all_data)

# --- 3. RESULT SAVE AUR RANK CALCULATE KARNE KA ROUTE ---
@app.route("/save_result", methods=["POST"])
def save_result():
    try:
        data = request.json 
        name = data.get("name", "Anjan")
        # Score ko number (float) mein badalna zaroori hai rank ke liye
        current_score = float(data.get("score", 0))

        path = "/Users/vikaschandra/Desktop/web_results.txt"
        
        # A. Naya result file mein save karein (Comma separated format for easy reading)
        with open(path, "a") as f:
            f.write(f"{name},{current_score}\n")

        # B. RANK LOGIC: Saari results padhkar rank nikalna
        all_scores = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        try:
                            all_scores.append(float(parts[1]))
                        except:
                            continue
        
        # Scores ko bade se chote (High to Low) sort karein
        all_scores.sort(reverse=True)
        
        # Rank dhoondna (index 0 se shuru hota hai isliye +1)
        rank = all_scores.index(current_score) + 1
        total_participants = len(all_scores)

        print(f"✅ Result Saved: {name} | Score: {current_score} | Rank: {rank}")

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
    app.run(debug=True)