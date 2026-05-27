import pandas as pd # pyright: ignore[reportMissingModuleSource]
import sqlite3
import os

DB_PATH  = "data/fitness.db"
CSV_PATH = "data/exercise_dataset.csv"

def load_csv_to_db():
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_csv(CSV_PATH)
    df.to_sql("exercises", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into fitness.db")
    print(f"Columns: {list(df.columns)}")
    conn.close()

if __name__ == "__main__":
    load_csv_to_db()