import pandas as pd
import sqlite3

# Define your CSV file paths

# Create or connect to SQLite DB
conn = sqlite3.connect("quiz_questions.db")
cursor = conn.cursor()

# Create the unified table with only necessary fields
# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS questions (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         question TEXT,
#         answer TEXT,
#         difficulty TEXT,
#         subject TEXT
#     )
               
#     """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE,
    email TEXT,
    role TEXT
) """)



# # Load each CSV, clean columns, and insert
# for subject, file in csv_files.items():
#     try:
#         df = pd.read_csv(file)

#         # Rename columns if needed and keep only necessary ones
#         df = df.rename(columns=lambda x: x.strip())  

#         required_columns = ["Question", "Answer", "Difficulty"]
#         if not all(col in df.columns for col in required_columns):
#             raise ValueError(f"{file} missing required columns.")

#         df = df[required_columns]
#         df["subject"] = subject

#         # Insert into SQLite
#         df.to_sql("questions", conn, if_exists="append", index=False)
#         print(f"{subject} questions inserted successfully.")

#     except Exception as e:
#         print(f"Error processing {subject} CSV: {e}")

# conn.close()
# print("✅ All CSVs loaded into SQLite successfully.")
