import sqlite3

# Connect to your database (change the name if it's different, e.g., gym.db)
conn = sqlite3.connect("data/fitness.db") 
c = conn.cursor()

try:
    # This manually adds the missing fiber column to your diet_log table
    c.execute("ALTER TABLE diet_log ADD COLUMN fiber REAL DEFAULT 0;")
    conn.commit()
    print("Successfully added the 'fiber' column!")
except sqlite3.OperationalError as e:
    print(f"Error or already updated: {e}")

conn.close()