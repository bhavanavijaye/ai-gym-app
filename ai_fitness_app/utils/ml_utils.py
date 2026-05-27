import joblib # pyright: ignore[reportMissingImports]
import numpy as np # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(BASE, "models")
DATA   = os.path.join(BASE, "data", "raw")


def _load(name):
    return joblib.load(os.path.join(MODELS, f"{name}.pkl"))


# ── Model 1: Calories Burned ──────────────────────────────────────────────────
def predict_calories(age, gender, weight_kg, height_cm, reps, sets,
                     duration_min, fitness_level, exercise, heart_rate_avg=140,
                     rest_seconds=60):
    model      = _load("calories_model")
    le_gender  = _load("le_gender")
    le_fitness = _load("le_fitness")
    le_ex      = _load("le_exercise")
    le_muscle  = _load("le_muscle")
    features   = _load("calories_features")

    bmi = weight_kg / ((height_cm / 100) ** 2)

    # MET lookup
    met_map = {
        'Barbell Squat':8.0,'Deadlift':7.5,'Bench Press':6.0,'Pull Up':8.0,
        'Push Up':3.8,'Bicep Curl':3.0,'Tricep Dip':3.5,'Shoulder Press':6.0,
        'Plank':4.0,'Burpee':8.0,'Jump Rope':11.0,'Running 6mph':9.8,
        'Cycling Moderate':8.0,'Swimming':7.0,'Rowing':7.0,'Lunges':4.0,
        'Leg Press':5.0,'Lat Pulldown':5.5,'Cable Row':5.0,'Incline Press':6.0,
        'Dumbbell Fly':4.5,'Leg Curl':4.5,'Leg Extension':4.0,'Calf Raise':2.5,
        'Face Pull':3.5,'Romanian Deadlift':6.5,'Hip Thrust':6.0,
        'Arnold Press':5.5,'Hammer Curl':3.2,'Skull Crusher':3.2,
        'Box Jump':8.5,'Mountain Climber':8.0,'Russian Twist':5.0,
        'Sit Up':3.0,'Battle Rope':10.0,'Kettlebell Swing':8.2,
        'TRX Row':5.0,'Dips':5.5,'Chin Up':8.0,'Sprint':14.0,
    }
    muscle_map = {
        'Barbell Squat':'Legs','Deadlift':'Back','Bench Press':'Chest',
        'Pull Up':'Back','Push Up':'Chest','Bicep Curl':'Arms',
        'Tricep Dip':'Arms','Shoulder Press':'Shoulders','Plank':'Core',
        'Burpee':'Full Body','Jump Rope':'Cardio','Running 6mph':'Cardio',
        'Cycling Moderate':'Cardio','Swimming':'Cardio','Rowing':'Full Body',
        'Lunges':'Legs','Leg Press':'Legs','Lat Pulldown':'Back',
        'Cable Row':'Back','Incline Press':'Chest','Dumbbell Fly':'Chest',
        'Leg Curl':'Legs','Leg Extension':'Legs','Calf Raise':'Legs',
        'Face Pull':'Shoulders','Romanian Deadlift':'Legs','Hip Thrust':'Legs',
        'Arnold Press':'Shoulders','Hammer Curl':'Arms','Skull Crusher':'Arms',
        'Box Jump':'Legs','Mountain Climber':'Core','Russian Twist':'Core',
        'Sit Up':'Core','Battle Rope':'Full Body','Kettlebell Swing':'Full Body',
        'TRX Row':'Back','Dips':'Chest','Chin Up':'Back','Sprint':'Cardio',
    }

    met = met_map.get(exercise, 6.0)
    muscle = muscle_map.get(exercise, 'Full Body')

    try:
        g_enc  = le_gender.transform([gender])[0]
        f_enc  = le_fitness.transform([fitness_level])[0]
        ex_enc = le_ex.transform([exercise])[0]
        m_enc  = le_muscle.transform([muscle])[0]
    except Exception:
        g_enc = 0; f_enc = 1; ex_enc = 0; m_enc = 0

    X = pd.DataFrame([[age, g_enc, weight_kg, height_cm, bmi, reps, sets,
                        duration_min, f_enc, met, heart_rate_avg, rest_seconds,
                        ex_enc, m_enc]], columns=features)
    return float(model.predict(X)[0])


# ── Model 2: Workout Frequency Recommender ────────────────────────────────────
def recommend_workout_freq(gender, age, weight_kg, height_cm, body_fat_pct,
                            muscle_mass_kg, waist_hip_ratio, fitness_score,
                            goal, bmi_category):
    model    = _load("workout_recommender_model")
    le_g     = _load("le_gender2")
    le_goal  = _load("le_goal")
    le_bmi   = _load("le_bmi_cat")
    le_freq  = _load("le_freq")
    features = _load("workout_rec_features")

    bmi = weight_kg / ((height_cm / 100) ** 2)
    try:
        g_enc    = le_g.transform([gender])[0]
        goal_enc = le_goal.transform([goal])[0]
        bmi_enc  = le_bmi.transform([bmi_category])[0]
    except Exception:
        g_enc = 0; goal_enc = 0; bmi_enc = 0

    X = pd.DataFrame([[g_enc, age, weight_kg, height_cm, bmi, body_fat_pct,
                        muscle_mass_kg, waist_hip_ratio, fitness_score,
                        goal_enc, bmi_enc]], columns=features)
    pred_enc = model.predict(X)[0]
    freq_label = le_freq.inverse_transform([pred_enc])[0]

    freq_map = {"Low": "1–2 days/week", "Moderate": "3 days/week",
                "High": "4–5 days/week", "Very High": "6–7 days/week"}
    return freq_label, freq_map.get(freq_label, "3 days/week")


# ── Model 3: Daily Calorie Goal ───────────────────────────────────────────────
def predict_calorie_goal(gender, age, weight_kg, height_cm, body_fat_pct,
                          muscle_mass_kg, workout_freq, fitness_score, goal):
    model    = _load("diet_calorie_model")
    le_g     = _load("le_gender3")
    le_goal  = _load("le_goal3")
    features = _load("diet_features")

    bmi = weight_kg / ((height_cm / 100) ** 2)
    bmi_cat = ('Underweight' if bmi < 18.5 else
                'Normal'      if bmi < 25   else
                'Overweight'  if bmi < 30   else 'Obese')

    try:
        g_enc    = le_g.transform([gender])[0]
        goal_enc = le_goal.transform([goal])[0]
    except Exception:
        g_enc = 0; goal_enc = 0

    X = pd.DataFrame([[g_enc, age, weight_kg, height_cm, bmi, body_fat_pct,
                        muscle_mass_kg, workout_freq, fitness_score, goal_enc]],
                     columns=features)
    cal = float(model.predict(X)[0])

    # Macro split based on goal
    macro_splits = {
        "Lose Weight":        (0.35, 0.40, 0.25),
        "Gain Muscle":        (0.30, 0.45, 0.25),
        "Maintain":           (0.25, 0.50, 0.25),
        "Improve Endurance":  (0.20, 0.55, 0.25),
    }
    p_pct, c_pct, f_pct = macro_splits.get(goal, (0.25, 0.50, 0.25))
    return {
        "calories":  round(cal),
        "protein_g": round(cal * p_pct / 4),
        "carbs_g":   round(cal * c_pct / 4),
        "fat_g":     round(cal * f_pct / 9),
        "bmi":       round(bmi, 1),
        "bmi_cat":   bmi_cat,
    }


# ── Model 4: Injury Risk ──────────────────────────────────────────────────────
def predict_injury_risk(age, gender, weight_kg, fitness_level,
                         weekly_training_hours, consecutive_days,
                         sleep_hours, stress_level, prev_injuries,
                         does_warm_up, does_cool_down):
    model    = _load("injury_risk_model")
    le_g     = _load("le_gender4")
    le_fit   = _load("le_fitness4")
    le_risk  = _load("le_risk")
    features = _load("injury_features")

    try:
        g_enc   = le_g.transform([gender])[0]
        fit_enc = le_fit.transform([fitness_level])[0]
    except Exception:
        g_enc = 0; fit_enc = 1

    X = pd.DataFrame([[age, g_enc, weight_kg, fit_enc, weekly_training_hours,
                        consecutive_days, sleep_hours, stress_level,
                        prev_injuries, int(does_warm_up), int(does_cool_down)]],
                     columns=features)
    pred_enc   = model.predict(X)[0]
    proba      = model.predict_proba(X)[0]
    risk_label = le_risk.inverse_transform([pred_enc])[0]

    classes = le_risk.classes_
    proba_dict = {classes[i]: round(float(proba[i]) * 100, 1) for i in range(len(classes))}

    tips_map = {
        "High":   ["🛑 Take a rest day immediately",
                   "🛑 Reduce weekly volume by 30%",
                   "🛑 Add warm-up and cool-down every session",
                   "🛑 Consult a physiotherapist if pain exists"],
        "Medium": ["⚠️ Add a proper warm-up (5–10 min)",
                   "⚠️ Limit to 4 sessions this week",
                   "⚠️ Prioritise 7–8 hrs sleep",
                   "⚠️ Manage stress with breathing or light yoga"],
        "Low":    ["✅ Great recovery habits — keep it up!",
                   "✅ You can safely increase intensity by 5–10%",
                   "✅ Stay consistent with warm-up & cool-down"],
    }
    return risk_label, proba_dict, tips_map.get(risk_label, [])


# ── Food Database Helper ──────────────────────────────────────────────────────
def get_food_database():
    path = os.path.join(DATA, "nutrition_dataset.csv")
    df = pd.read_csv(path)
    return df.drop_duplicates(subset=["food_name"]).reset_index(drop=True)


def get_exercise_list():
    path = os.path.join(DATA, "exercise_dataset.csv")
    df = pd.read_csv(path)
    return sorted(df["exercise"].unique().tolist())