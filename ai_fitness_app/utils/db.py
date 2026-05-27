import sqlite3
import os
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fitness.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── Original tables ────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            exercise TEXT,
            reps INTEGER,
            sets INTEGER,
            calories INTEGER,
            score REAL,
            weight_kg REAL DEFAULT 0,
            form_score REAL DEFAULT 0,
            notes TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS diet_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            meal TEXT,
            meal_type TEXT DEFAULT 'Other',
            calories INTEGER,
            protein REAL,
            carbs REAL,
            fat REAL,
            fiber REAL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            completed INTEGER,
            mood INTEGER,
            notes TEXT,
            sleep_hours REAL DEFAULT 0,
            energy_level INTEGER DEFAULT 5,
            water_ml INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    # ── NEW: Body stats ────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS body_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            weight_kg REAL,
            body_fat_pct REAL DEFAULT 0,
            chest_cm REAL DEFAULT 0,
            waist_cm REAL DEFAULT 0,
            hips_cm REAL DEFAULT 0,
            bicep_cm REAL DEFAULT 0,
            thigh_cm REAL DEFAULT 0,
            notes TEXT DEFAULT ''
        )
    """)

    # ── NEW: Personal Records ──────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS personal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            exercise TEXT,
            weight_kg REAL,
            reps INTEGER,
            notes TEXT DEFAULT ''
        )
    """)

    # ── NEW: Water log ─────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS water_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount_ml INTEGER,
            time TEXT
        )
    """)

    # ── NEW: Sleep log ─────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            hours REAL,
            quality INTEGER,
            bedtime TEXT DEFAULT '',
            wake_time TEXT DEFAULT ''
        )
    """)

    # ── NEW: Workout programs ──────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS workout_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_date TEXT,
            name TEXT,
            program_text TEXT,
            level TEXT,
            days_per_week INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ── Workout functions ──────────────────────────────────────────────────────────
def log_workout(exercise, reps, sets, calories, score, weight_kg=0, form_score=0, notes=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO workouts (date, exercise, reps, sets, calories, score, weight_kg, form_score, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (str(date.today()), exercise, reps, sets, calories, score, weight_kg, form_score, notes)
    )
    # Auto-update personal record if weight > previous best
    if weight_kg > 0:
        c.execute(
            "SELECT MAX(weight_kg) FROM personal_records WHERE exercise=?", (exercise,)
        )
        row = c.fetchone()
        current_best = row[0] if row[0] else 0
        if weight_kg > current_best:
            c.execute(
                "INSERT INTO personal_records (date, exercise, weight_kg, reps, notes) VALUES (?,?,?,?,?)",
                (str(date.today()), exercise, weight_kg, reps, "Auto-logged PR")
            )
    conn.commit()
    conn.close()


def get_workout_history(limit=30):
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT date, exercise, reps, sets, calories, weight_kg, form_score FROM workouts ORDER BY date DESC LIMIT ?",
            conn, params=(limit,)
        )
    except Exception:
        df = pd.DataFrame(columns=["date", "exercise", "reps", "sets", "calories", "weight_kg", "form_score"])
    conn.close()
    return df


def get_exercise_progress(exercise):
    """Returns historical data for one exercise to chart progress."""
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT date, reps, sets, weight_kg, form_score FROM workouts WHERE exercise=? ORDER BY date ASC",
            conn, params=(exercise,)
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ── Diet functions ─────────────────────────────────────────────────────────────
def log_meal(meal, calories, protein, carbs, fat, meal_type="Other", fiber=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO diet_log (date, meal, meal_type, calories, protein, carbs, fat, fiber) VALUES (?,?,?,?,?,?,?,?)",
        (str(date.today()), meal, meal_type, calories, protein, carbs, fat, fiber)
    )
    conn.commit()
    conn.close()


def get_today_calories():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), SUM(fiber) FROM diet_log WHERE date=?",
        (str(date.today()),)
    )
    row = c.fetchone()
    conn.close()
    return {
        "calories": row[0] or 0,
        "protein": row[1] or 0,
        "carbs": row[2] or 0,
        "fat": row[3] or 0,
        "fiber": row[4] or 0,
    }


def get_diet_history(days=30):
    conn = get_conn()
    try:
        since = str(date.today() - timedelta(days=days))
        df = pd.read_sql_query(
            "SELECT date, meal, meal_type, calories, protein, carbs, fat FROM diet_log WHERE date >= ? ORDER BY date DESC",
            conn, params=(since,)
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ── Habit functions ────────────────────────────────────────────────────────────
def log_habit(completed, mood, notes, sleep_hours=0, energy_level=5, water_ml=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO habits (date, completed, mood, notes, sleep_hours, energy_level, water_ml) VALUES (?,?,?,?,?,?,?)",
        (str(date.today()), completed, mood, notes, sleep_hours, energy_level, water_ml)
    )
    conn.commit()
    conn.close()


def get_habit_history(limit=30):
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT date, completed, mood, sleep_hours, energy_level, water_ml FROM habits ORDER BY date DESC LIMIT ?",
            conn, params=(limit,)
        )
    except Exception:
        df = pd.DataFrame(columns=["date", "completed", "mood", "sleep_hours", "energy_level", "water_ml"])
    conn.close()
    return df


# ── Body stats functions ───────────────────────────────────────────────────────
def log_body_stats(weight_kg, body_fat_pct=0, chest_cm=0, waist_cm=0,
                   hips_cm=0, bicep_cm=0, thigh_cm=0, notes=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO body_stats (date, weight_kg, body_fat_pct, chest_cm, waist_cm,
           hips_cm, bicep_cm, thigh_cm, notes) VALUES (?,?,?,?,?,?,?,?,?)""",
        (str(date.today()), weight_kg, body_fat_pct, chest_cm, waist_cm,
         hips_cm, bicep_cm, thigh_cm, notes)
    )
    conn.commit()
    conn.close()


def get_body_stats_history():
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM body_stats ORDER BY date ASC",
            conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_latest_body_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM body_stats ORDER BY date DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "date": row[1], "weight_kg": row[2], "body_fat_pct": row[3],
            "chest_cm": row[4], "waist_cm": row[5], "hips_cm": row[6],
            "bicep_cm": row[7], "thigh_cm": row[8]
        }
    return None


# ── Water functions ────────────────────────────────────────────────────────────
def log_water(amount_ml):
    from datetime import datetime
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO water_log (date, amount_ml, time) VALUES (?,?,?)",
        (str(date.today()), amount_ml, datetime.now().strftime("%H:%M"))
    )
    conn.commit()
    conn.close()


def get_today_water():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount_ml) FROM water_log WHERE date=?", (str(date.today()),))
    row = c.fetchone()
    conn.close()
    return row[0] or 0


def get_water_history(days=14):
    conn = get_conn()
    try:
        since = str(date.today() - timedelta(days=days))
        df = pd.read_sql_query(
            "SELECT date, SUM(amount_ml) as total_ml FROM water_log WHERE date >= ? GROUP BY date ORDER BY date ASC",
            conn, params=(since,)
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ── Sleep functions ────────────────────────────────────────────────────────────
def log_sleep(hours, quality, bedtime="", wake_time=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sleep_log (date, hours, quality, bedtime, wake_time) VALUES (?,?,?,?,?)",
        (str(date.today()), hours, quality, bedtime, wake_time)
    )
    conn.commit()
    conn.close()


def get_sleep_history(days=30):
    conn = get_conn()
    try:
        since = str(date.today() - timedelta(days=days))
        df = pd.read_sql_query(
            "SELECT date, hours, quality FROM sleep_log WHERE date >= ? ORDER BY date ASC",
            conn, params=(since,)
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ── Personal Records ───────────────────────────────────────────────────────────
def get_personal_records():
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            """SELECT exercise, MAX(weight_kg) as best_weight, date
               FROM personal_records GROUP BY exercise ORDER BY best_weight DESC""",
            conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def log_personal_record(exercise, weight_kg, reps, notes=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO personal_records (date, exercise, weight_kg, reps, notes) VALUES (?,?,?,?,?)",
        (str(date.today()), exercise, weight_kg, reps, notes)
    )
    conn.commit()
    conn.close()


# ── Workout programs ───────────────────────────────────────────────────────────
def save_workout_program(name, program_text, level, days_per_week):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO workout_programs (created_date, name, program_text, level, days_per_week) VALUES (?,?,?,?,?)",
        (str(date.today()), name, program_text, level, days_per_week)
    )
    conn.commit()
    conn.close()


def get_saved_programs():
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT id, created_date, name, level, days_per_week FROM workout_programs ORDER BY created_date DESC",
            conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_program_by_id(program_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM workout_programs WHERE id=?", (program_id,))
    row = c.fetchone()
    conn.close()
    return row


# ── Dashboard summary ──────────────────────────────────────────────────────────
def get_weekly_summary():
    conn = get_conn()
    c = conn.cursor()
    week_ago = str(date.today() - timedelta(days=7))

    c.execute("SELECT COUNT(*), SUM(calories) FROM workouts WHERE date >= ?", (week_ago,))
    w = c.fetchone()

    c.execute("SELECT COUNT(*) FROM habits WHERE completed=1 AND date >= ?", (week_ago,))
    h = c.fetchone()

    c.execute("SELECT AVG(mood) FROM habits WHERE date >= ?", (week_ago,))
    mood_row = c.fetchone()

    c.execute("SELECT AVG(hours) FROM sleep_log WHERE date >= ?", (week_ago,))
    sleep_row = c.fetchone()

    # Build chart data
    c.execute(
        "SELECT date, SUM(calories) as calories, exercise as type FROM workouts WHERE date >= ? GROUP BY date",
        (week_ago,)
    )
    rows = c.fetchall()
    weekly_data = [{"day": r[0][-5:], "calories": r[1] or 0, "type": r[2] or "workout"} for r in rows]

    conn.close()
    return {
        "workouts": w[0] or 0,
        "calories_burned": w[1] or 0,
        "diet_score": 7,
        "streak": h[0] or 0,
        "avg_mood": round(mood_row[0] or 0, 1),
        "avg_sleep": round(sleep_row[0] or 0, 1),
        "weekly_data": weekly_data,
    }


def get_full_context_for_ai():
    """Returns a text summary of recent user data for AI context injection."""
    summary = get_weekly_summary()
    body = get_latest_body_stats()
    today_cals = get_today_calories()
    water = get_today_water()
    prs = get_personal_records()

    lines = [
        f"USER FITNESS CONTEXT (last 7 days):",
        f"- Workouts completed: {summary['workouts']}",
        f"- Calories burned: {summary['calories_burned']} kcal",
        f"- Workout streak: {summary['streak']} days",
        f"- Average mood: {summary['avg_mood']}/10",
        f"- Average sleep: {summary['avg_sleep']} hours",
        f"- Today's calories consumed: {today_cals['calories']:.0f} kcal",
        f"- Today's macros: Protein {today_cals['protein']:.0f}g, Carbs {today_cals['carbs']:.0f}g, Fat {today_cals['fat']:.0f}g",
        f"- Today's water intake: {water} ml",
    ]
    if body:
        lines.append(f"- Current weight: {body['weight_kg']} kg")
        if body['body_fat_pct']:
            lines.append(f"- Body fat: {body['body_fat_pct']}%")
    if not prs.empty:
        pr_list = ", ".join([f"{row['exercise']} {row['best_weight']}kg" for _, row in prs.head(5).iterrows()])
        lines.append(f"- Personal records: {pr_list}")

    return "\n".join(lines)
import bcrypt # pyright: ignore[reportMissingImports]

# REGISTER USER
def create_user(email, password):

    conn = get_conn()
    c = conn.cursor()

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    )

    try:
        c.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, hashed)
        )

        conn.commit()
        return True

    except:
        return False

    finally:
        conn.close()


# LOGIN USER
def login_user(email, password):

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT password FROM users WHERE email=?",
        (email,)
    )

    user = c.fetchone()

    conn.close()

    if user:

        stored_password = user[0]

        return bcrypt.checkpw(
            password.encode(),
            stored_password
        )

    return False