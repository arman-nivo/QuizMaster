from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
from transformers import MT5ForConditionalGeneration, MT5Tokenizer
import pandas as pd
import sqlite3

app = Flask(__name__)

# Enable CORS for specific origin (React frontend at localhost:3000)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Load the dataset from Google Sheets
file_path = "https://docs.google.com/spreadsheets/d/1rRMDhMwucike2GiAHyadR3NflMkuCsSKeI10geklpio/export?format=csv"

try:
    dataset = pd.read_csv(file_path)
    if dataset.empty:
        raise ValueError("Dataset is empty.")
    print("Dataset loaded successfully!")
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = None

# Load SentenceTransformer model
print("Loading SentenceTransformer model...")

sentence_model = SentenceTransformer("bert-base-multilingual-cased")

# Load mT5 model
print("Loading mT5 model...")
mt5_model = MT5ForConditionalGeneration.from_pretrained("google/mt5-small")
tokenizer = MT5Tokenizer.from_pretrained("google/mt5-small")

@app.route("/")
def home():
    return "Backend is running! Use '/generate_questions' and '/validate_answer' endpoints."

# Endpoint to generate questions
@app.route("/generate_questions", methods=["POST"])
def generate_questions():
    if dataset is None or dataset.empty:
        return jsonify({"error": "Dataset not loaded properly."}), 500

    data = request.json

    # Validate the `num_questions` parameter
    try:
        num_questions = int(data.get("num_questions", 5))  # Default to 5 questions
        if num_questions <= 0:
            raise ValueError("Number of questions must be greater than zero.")
    except ValueError as e:
        return jsonify({"error": f"Invalid input for 'num_questions': {e}"}), 400

    # Select random questions from the dataset
    selected_questions = dataset.sample(n=min(num_questions, len(dataset))).to_dict(orient="records")
    print(f"Generated {len(selected_questions)} questions.")

    return jsonify({"questions": selected_questions})

# Endpoint to validate user's answer
@app.route("/validate_answer", methods=["POST"])
def validate_answer():
    data = request.json
    user_answer = data.get("user_answer", "")
    correct_answer = data.get("correct_answer", "")

    if not user_answer or not correct_answer:
        return jsonify({"error": "Both 'user_answer' and 'correct_answer' must be provided."}), 400

    similarity_threshold = 0.7  # Define similarity threshold

    # Calculate similarity score
    user_embedding = sentence_model.encode(user_answer, convert_to_tensor=True)
    correct_embedding = sentence_model.encode(correct_answer, convert_to_tensor=True)
    similarity = util.cos_sim(user_embedding, correct_embedding).item()

    # Determine if the answer is correct
    is_correct = similarity >= similarity_threshold
    print(f"User Answer: {user_answer} | Correct Answer: {correct_answer} | Similarity: {similarity} | Correct: {is_correct}")

    return jsonify({
        "is_correct": is_correct,
        "similarity": round(similarity, 2)
    })

DATABASE = "quiz_results.db"

# Initialize the database
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

@app.route("/save_results", methods=["POST"])
def save_results():
    data = request.json
    results = data.get("results", [])
    print("Results received for saving:", results)  # Debug log

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        for result in results:
            cursor.execute("""
                INSERT INTO results (question, user_answer, correct_answer, is_correct, similarity)
                VALUES (?, ?, ?, ?, ?)
            """, (result["question"], result["userAnswer"], result["correctAnswer"], int(result["isCorrect"]), result["similarity"]))
        conn.commit()
        conn.close()
        return jsonify({"message": "Results saved successfully!"}), 200
    except Exception as e:
        print("Error saving results:", e)  # Debug log
        return jsonify({"error": f"Failed to save results: {str(e)}"}), 500



@app.route("/get_results", methods=["GET"])
def get_results():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT question, user_answer, correct_answer, is_correct, similarity, timestamp FROM results")
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
        print("Fetched results:", results)  # Debug log
        return jsonify(results)
    except Exception as e:
        print("Error fetching results:", e)  # Debug log
        return jsonify({"error": f"Failed to fetch results: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
