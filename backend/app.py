from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
from transformers import MT5ForConditionalGeneration, MT5Tokenizer
import pandas as pd
import sqlite3
import random  # ✅ Required for shuffle

app = Flask(__name__)
# Enable CORS for specific origin (React frontend at localhost:3000)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})





# Load SentenceTransformer model
print("Loading SentenceTransformer model...")
sentence_model = SentenceTransformer("bert-base-multilingual-cased")



# Load mT5 model
print("Loading mT5 model...")
mt5_model = MT5ForConditionalGeneration.from_pretrained("google/mt5-small")
tokenizer = MT5Tokenizer.from_pretrained("google/mt5-small")



# Database configuration
DATABASE = "quiz_results.db"
QUESTION_DB = "quiz_questions.db"

# Initialize the results database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct INTEGER,
            similarity REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "Backend is running! Use '/generate_questions' and '/validate_answer' endpoints."


# ✅ Generate Questions
@app.route("/generate_custom_questions", methods=["POST"])
def generate_custom_questions():
    data = request.json
    subject = data.get("subject", "ICT").lower()
    easy_count = int(data.get("easy", 0))
    medium_count = int(data.get("medium", 0))
    hard_count = int(data.get("hard", 0))

    total_requested = easy_count + medium_count + hard_count
    if total_requested == 0:
        return jsonify({"error": "No questions requested."}), 400

    all_questions = []

    try:
        conn = sqlite3.connect(QUESTION_DB)
        cursor = conn.cursor()

        difficulty_map = {
            "easy": easy_count,
            "medium": medium_count,
            "hard": hard_count
        }

        for level, count in difficulty_map.items():
            if count <= 0:
                continue

            cursor.execute("""
                SELECT question, answer, difficulty, subject
                FROM questions
                WHERE lower(difficulty) = ? AND lower(subject) = ?
                ORDER BY RANDOM()
                LIMIT ?
            """, (level, subject, count))

            rows = cursor.fetchall()
            if len(rows) < count:
                return jsonify({"error": f"Not enough '{level}' questions for subject {subject.title()}."}), 400

            for row in rows:
                all_questions.append({
                    "Question": row[0],
                    "Answer": row[1],
                    "Difficulty": row[2],
                    "Subject": row[3]
                })

        conn.close()
        random.shuffle(all_questions)

        return jsonify({"questions": all_questions})

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


import unicodedata

def normalize_text(text):
    return unicodedata.normalize("NFKC", text.strip().lower())



@app.route("/validate_answer", methods=["POST"])
def validate_answer():
    data = request.json
    user_answer = normalize_text(data.get("user_answer", ""))
    correct_answer = normalize_text(data.get("correct_answer", ""))

    if not user_answer or not correct_answer:
        return jsonify({"error": "Both 'user_answer' and 'correct_answer' must be provided."}), 400

    similarity_threshold = 0.65  # Consider lowering for Bangla

    # Encode
    user_embedding = sentence_model.encode(user_answer, convert_to_tensor=True)
    correct_embedding = sentence_model.encode(correct_answer, convert_to_tensor=True)

    similarity = util.cos_sim(user_embedding, correct_embedding).item()
    is_correct = similarity >= similarity_threshold

    print(f"User Answer: {user_answer} | Correct: {correct_answer} | Similarity: {similarity:.2f} | Correct: {is_correct}")

    return jsonify({
        "is_correct": is_correct,
        "similarity": round(similarity, 2)
    })




# ✅ Save Results
@app.route("/save_results", methods=["POST"])
def save_results():
    data = request.json
    results = data.get("results", [])
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        for result in results:
            cursor.execute("""
                INSERT INTO results (question, user_answer, correct_answer, is_correct, similarity)
                VALUES (?, ?, ?, ?, ?)
            """, (
                result["question"],
                result["userAnswer"],
                result["correctAnswer"],
                int(result["isCorrect"]),
                result["similarity"]
            ))
        conn.commit()
        conn.close()
        return jsonify({"message": "Results saved successfully!"}), 200
    except Exception as e:
        print("Error saving results:", e)
        return jsonify({"error": f"Failed to save results: {str(e)}"}), 500


@app.route("/sample_questions", methods=["GET"])
def sample_questions():
    try:
        conn = sqlite3.connect("quiz_questions.db")
        df = pd.read_sql_query("SELECT * FROM questions ORDER BY RANDOM() LIMIT 5", conn)
        conn.close()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ✅ Add/Edit/Delete Questions

@app.route("/add_question", methods=["POST"])
def add_question():
    data = request.get_json()
    q, a, d, s = data.get("question"), data.get("answer"), data.get("difficulty"), data.get("subject")
    if not all([q, a, d, s]):
        return jsonify({"error": "All fields required"}), 400

    conn = sqlite3.connect(QUESTION_DB)      # <-- use QUESTION_DB here
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    """)
    cursor.execute(
        "INSERT INTO questions (question, answer, difficulty, subject) VALUES (?, ?, ?, ?)",
        (q, a, d, s)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Question added"}), 200


@app.route("/edit_question/<int:qid>", methods=["PUT"])
def edit_question(qid):
    data = request.get_json()
    q, a, d, s = data.get("question"), data.get("answer"), data.get("difficulty"), data.get("subject")
    if not all([q, a, d, s]):
        return jsonify({"error": "All fields required"}), 400

    conn = sqlite3.connect(QUESTION_DB)    # <-- use QUESTION_DB here
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE questions SET question = ?, answer = ?, difficulty = ?, subject = ? WHERE id = ?",
        (q, a, d, s, qid)
    )
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Question not found"}), 404

    conn.commit()
    conn.close()
    return jsonify({"message": "Question updated"}), 200


@app.route("/delete_question/<int:qid>", methods=["DELETE"])
def delete_question(qid):
    conn = sqlite3.connect(QUESTION_DB)    # <-- use QUESTION_DB here
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (qid,))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Question not found"}), 404

    conn.commit()
    conn.close()
    return jsonify({"message": "Question deleted"}), 200


# ✅ Get Results
@app.route("/get_results", methods=["GET"])
def get_results():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question, user_answer, correct_answer, is_correct, similarity, timestamp
            FROM results
        """)
        rows = cursor.fetchall()
        conn.close()

        results = [
            {
                "question": row[0],
                "userAnswer": row[1],
                "correctAnswer": row[2],
                "isCorrect": bool(row[3]),
                "similarity": row[4],
                "timestamp": row[5]
            }
            for row in rows
        ]
        return jsonify(results)
    except Exception as e:
        print("Error fetching results:", e)
        return jsonify({"error": f"Failed to fetch results: {str(e)}"}), 500

# all question show   
@app.route("/all_questions", methods=["GET"])
def all_questions():
    conn = sqlite3.connect(QUESTION_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, difficulty, subject FROM questions")
    rows = cursor.fetchall()
    conn.close()

    questions = [
        {"id": r[0], "question": r[1], "answer": r[2], "difficulty": r[3], "subject": r[4]}
        for r in rows
    ]
    return jsonify({"questions": questions})




if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
