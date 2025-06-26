import sqlite3
import pandas as pd

# Connect to your SQLite database
conn = sqlite3.connect("quiz_questions.db")

# Load the data from the table
df = pd.read_sql_query("SELECT * FROM questions", conn)

# Show first 5 rows
print(df.head())  # Use df.sample(5) for random sample

# Or random sample of 10 rows
print(df.sample(10))

conn.close()
