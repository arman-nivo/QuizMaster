from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import re

app = Flask(__name__)

# Enable CORS for the Flask app
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Load the dataset from Google Sheets
file_path = "https://docs.google.com/spreadsheets/d/1veRQYB_hZibBXUF_3_cKon3XiOgAkUBszhhbAXGXZyU/export?format=csv"

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
sentence_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


# Preprocess text function
def preprocess_text(text):
    text = text.lower().strip()  # Lowercase and trim spaces
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    return text


# Keyword matching function
def keyword_check(user_answer, correct_answer):
    keywords = correct_answer.split()  # Split correct answer into keywords
    return any(keyword in user_answer for keyword in keywords)


# Home endpoint
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

    # Preprocess text
    user_answer_processed = preprocess_text(user_answer)
    correct_answer_processed = preprocess_text(correct_answer)

    # Calculate similarity score
    user_embedding = sentence_model.encode(user_answer_processed, convert_to_tensor=True)
    correct_embedding = sentence_model.encode(correct_answer_processed, convert_to_tensor=True)
    similarity = util.cos_sim(user_embedding, correct_embedding).item()

    # Check if the similarity is above the threshold or if keywords match
    is_correct = similarity >= similarity_threshold or keyword_check(user_answer_processed, correct_answer_processed)

    print(f"User Answer: {user_answer} | Correct Answer: {correct_answer} | Similarity: {similarity} | Correct: {is_correct}")

    return jsonify({
        "is_correct": is_correct,
        "similarity": round(similarity, 2)
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
