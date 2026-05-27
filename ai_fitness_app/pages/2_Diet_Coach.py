import streamlit as st # pyright: ignore[reportMissingImports]
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from utils.sidebar import show_sidebar
from groq import Groq # pyright: ignore[reportMissingImports]
from utils.db import (
    log_meal, get_today_calories, get_diet_history,
    log_water, get_today_water, get_water_history
)
import os
show_sidebar()
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]

load_dotenv()

st.set_page_config(page_title="Diet Coach", page_icon="🥗", layout="wide")
st.title("🥗 AI Diet & Calorie Coach")

GROQ_MODEL = "llama-3.1-8b-instant"

# ── Indian + Common food database ──────────────────────────────────────────────
FOOD_DB = {
    # Indian staples
    "Chapati / Roti (1 piece)": {"cal": 104, "protein": 3.1, "carbs": 20.0, "fat": 1.9, "fiber": 2.7},
    "Idli (2 pieces)": {"cal": 78, "protein": 2.8, "carbs": 15.0, "fat": 0.3, "fiber": 0.5},
    "Dosa (1 plain)": {"cal": 133, "protein": 3.5, "carbs": 25.0, "fat": 2.7, "fiber": 1.0},
    "Upma (1 cup)": {"cal": 220, "protein": 4.0, "carbs": 38.0, "fat": 6.0, "fiber": 2.0},
    "Dal (1 cup cooked)": {"cal": 230, "protein": 15.6, "carbs": 39.0, "fat": 1.0, "fiber": 8.0},
    "Rice (1 cup cooked)": {"cal": 206, "protein": 4.2, "carbs": 44.5, "fat": 0.4, "fiber": 0.6},
    "Chicken Curry (1 cup)": {"cal": 280, "protein": 26.0, "carbs": 8.0, "fat": 16.0, "fiber": 1.5},
    "Paneer (100g)": {"cal": 265, "protein": 18.3, "carbs": 1.2, "fat": 20.8, "fiber": 0},
    "Rajma (1 cup)": {"cal": 225, "protein": 13.4, "carbs": 40.4, "fat": 0.9, "fiber": 13.1},
    "Chole (1 cup)": {"cal": 269, "protein": 14.5, "carbs": 45.0, "fat": 4.3, "fiber": 12.5},
    "Sambar (1 cup)": {"cal": 92, "protein": 3.8, "carbs": 15.0, "fat": 2.0, "fiber": 4.0},
    "Biryani (1 cup)": {"cal": 290, "protein": 12.0, "carbs": 45.0, "fat": 8.0, "fiber": 1.5},
    "Puri (1 piece)": {"cal": 105, "protein": 1.8, "carbs": 14.5, "fat": 4.8, "fiber": 0.5},
    "Paratha (1 piece, plain)": {"cal": 188, "protein": 4.4, "carbs": 25.0, "fat": 8.0, "fiber": 2.0},
    "Aloo Sabzi (1 cup)": {"cal": 150, "protein": 3.0, "carbs": 28.0, "fat": 3.5, "fiber": 3.5},
    "Lassi (1 glass, sweet)": {"cal": 218, "protein": 6.0, "carbs": 32.0, "fat": 7.0, "fiber": 0},
    "Masala Chai (1 cup with milk/sugar)": {"cal": 60, "protein": 2.0, "carbs": 9.0, "fat": 2.0, "fiber": 0},
    # International / common
    "Boiled Egg (1 large)": {"cal": 78, "protein": 6.3, "carbs": 0.6, "fat": 5.3, "fiber": 0},
    "Banana (1 medium)": {"cal": 105, "protein": 1.3, "carbs": 27.0, "fat": 0.4, "fiber": 3.1},
    "Apple (1 medium)": {"cal": 95, "protein": 0.5, "carbs": 25.1, "fat": 0.3, "fiber": 4.4},
    "Whole Milk (1 cup)": {"cal": 149, "protein": 8.0, "carbs": 11.7, "fat": 8.0, "fiber": 0},
    "Chicken Breast (100g grilled)": {"cal": 165, "protein": 31.0, "carbs": 0, "fat": 3.6, "fiber": 0},
    "Brown Rice (1 cup cooked)": {"cal": 216, "protein": 5.0, "carbs": 44.8, "fat": 1.8, "fiber": 3.5},
    "Oats (1 cup cooked)": {"cal": 154, "protein": 5.5, "carbs": 27.4, "fat": 2.6, "fiber": 4.0},
    "Greek Yogurt (100g)": {"cal": 59, "protein": 10.0, "carbs": 3.6, "fat": 0.4, "fiber": 0},
    "Avocado (1/2 medium)": {"cal": 120, "protein": 1.5, "carbs": 6.4, "fat": 11.0, "fiber": 5.0},
    "Almonds (30g / ~23 nuts)": {"cal": 172, "protein": 6.3, "carbs": 6.1, "fat": 14.9, "fiber": 3.4},
    "Protein Shake (30g scoop)": {"cal": 120, "protein": 24.0, "carbs": 4.0, "fat": 2.0, "fiber": 1.0},
    "White Bread (2 slices)": {"cal": 132, "protein": 4.0, "carbs": 25.0, "fat": 1.5, "fiber": 1.2},
    "Peanut Butter (2 tbsp)": {"cal": 190, "protein": 8.0, "carbs": 6.0, "fat": 16.0, "fiber": 2.0},
}

MEAL_TYPES = ["Breakfast", "Morning Snack", "Lunch", "Evening Snack", "Dinner", "Post-Workout", "Other"]

tabs = st.tabs(["📋 Log Meal", "💧 Water Tracker", "🤖 AI Meal Plan", "📊 Nutrition Summary", "📅 Diet History"])

# ── Tab 1: Log Meal ────────────────────────────────────────────────────────────
with tabs[0]:
    col_manual, col_quick = st.columns(2)

    with col_quick:
        st.subheader("⚡ Quick Add from Food Database")
        food_choice = st.selectbox("Search food", ["— Select —"] + sorted(FOOD_DB.keys()))
        meal_type_q = st.selectbox("Meal type", MEAL_TYPES, key="qt_type")
        qty = st.number_input("Quantity (servings)", 0.5, 10.0, 1.0, step=0.5)

        if food_choice != "— Select —":
            fd = FOOD_DB[food_choice]
            st.info(
                f"**{food_choice}** × {qty}\n\n"
                f"🔥 {fd['cal']*qty:.0f} kcal  |  "
                f"🥩 {fd['protein']*qty:.1f}g protein  |  "
                f"🍞 {fd['carbs']*qty:.1f}g carbs  |  "
                f"🧈 {fd['fat']*qty:.1f}g fat  |  "
                f"🌿 {fd['fiber']*qty:.1f}g fiber"
            )
        if st.button("➕ Quick Add", type="primary", use_container_width=True):
            if food_choice != "— Select —":
                fd = FOOD_DB[food_choice]
                log_meal(
                    f"{food_choice} × {qty}", int(fd["cal"] * qty),
                    fd["protein"] * qty, fd["carbs"] * qty, fd["fat"] * qty,
                    meal_type_q, fd["fiber"] * qty
                )
                st.success(f"✅ Added: {food_choice}")
                st.rerun()
            else:
                st.warning("Select a food first")

    with col_manual:
        st.subheader("✏️ Manual Entry")
        meal_name = st.text_input("Meal name", placeholder="e.g. Homemade dal rice")
        meal_type_m = st.selectbox("Meal type", MEAL_TYPES, key="m_type")

        mc1, mc2 = st.columns(2)
        with mc1:
            cal = st.number_input("Calories (kcal)", 0, 3000, 400)
            protein = st.number_input("Protein (g)", 0.0, 200.0, 30.0)
            fiber = st.number_input("Fiber (g)", 0.0, 100.0, 3.0)
        with mc2:
            carbs = st.number_input("Carbs (g)", 0.0, 400.0, 50.0)
            fat = st.number_input("Fat (g)", 0.0, 100.0, 10.0)

        if st.button("➕ Log Meal", type="primary", use_container_width=True):
            if meal_name.strip():
                log_meal(meal_name, cal, protein, carbs, fat, meal_type_m, fiber)
                st.success(f"✅ {meal_name} logged!")
                st.rerun()
            else:
                st.warning("Enter a meal name")

# ── Tab 2: Water Tracker ───────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("💧 Daily Water Intake Tracker")
    water_goal_ml = st.slider("Daily goal (ml)", 1500, 4000, 2500, 250)
    today_water = get_today_water()
    remaining_water = max(water_goal_ml - today_water, 0)

    w1, w2, w3 = st.columns(3)
    w1.metric("Today", f"{today_water} ml")
    w2.metric("Goal", f"{water_goal_ml} ml")
    w3.metric("Remaining", f"{remaining_water} ml")

    water_pct = min(today_water / water_goal_ml, 1.0)
    if water_pct >= 1.0:
        st.success("🎉 Daily water goal reached!")
    else:
        st.progress(water_pct, text=f"{today_water}/{water_goal_ml} ml")

    # Quick add buttons
    st.subheader("Quick Add")
    bw1, bw2, bw3, bw4, bw5 = st.columns(5)
    amounts = [150, 250, 330, 500, 750]
    labels = ["☕ 150ml", "🥤 250ml", "🥤 330ml", "🍶 500ml", "🍾 750ml"]
    for col, amt, lbl in zip([bw1, bw2, bw3, bw4, bw5], amounts, labels):
        with col:
            if st.button(lbl, use_container_width=True):
                log_water(amt)
                st.rerun()

    custom_water = st.number_input("Custom amount (ml)", 50, 2000, 200, step=50)
    if st.button("Add Custom Amount", use_container_width=True):
        log_water(custom_water)
        st.rerun()

    # Water history chart
    st.divider()
    water_hist = get_water_history(14)
    if not water_hist.empty:
        water_hist["date"] = pd.to_datetime(water_hist["date"])
        fig_wh = px.bar(water_hist, x="date", y="total_ml",
                        title="Water Intake — Last 14 Days",
                        color_discrete_sequence=["#378ADD"])
        fig_wh.add_hline(y=water_goal_ml, line_dash="dash",
                         annotation_text=f"Goal {water_goal_ml}ml",
                         line_color="rgba(100,200,100,0.6)")
        fig_wh.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)", height=280)
        st.plotly_chart(fig_wh, use_container_width=True)

# ── Tab 3: AI Meal Plan ────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("🤖 AI Personalized Meal Plan Generator")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        weight = st.number_input("Weight (kg)", 40, 200, 70, key="mp_w")
        height = st.number_input("Height (cm)", 140, 220, 170, key="mp_h")
        age = st.number_input("Age", 15, 80, 25, key="mp_age")
    with ac2:
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        goal = st.selectbox("Goal", ["Lose weight", "Gain muscle", "Maintain weight",
                                     "Athletic performance", "Improve health"])
        diet_type = st.selectbox("Diet type", ["No restriction", "Vegetarian", "Vegan",
                                                "Keto", "High protein", "Sattvic",
                                                "South Indian", "North Indian"])
    with ac3:
        activity = st.selectbox("Activity level", ["Sedentary", "Lightly Active",
                                                    "Moderately Active", "Very Active", "Athlete"])
        budget = st.selectbox("Budget", ["Economy (under ₹200/day)", "Moderate (₹200-500/day)",
                                          "Generous (₹500+/day)"])
        allergies = st.text_input("Allergies / avoidances", placeholder="e.g. nuts, dairy, gluten")

    plan_days = st.radio("Plan duration", ["1 day", "3 days", "7 days"], horizontal=True)

    if st.button("🍽️ Generate My Meal Plan", type="primary", use_container_width=True):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY not found in .env")
        else:
            bmi = weight / ((height / 100) ** 2)
            with st.spinner("Crafting your personalized plan..."):
                try:
                    client = Groq(api_key=api_key)
                    resp = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{
                            "role": "user",
                            "content": f"""Create a detailed {plan_days} meal plan for:
- Age: {age}, Gender: {gender}, BMI: {bmi:.1f}
- Goal: {goal}
- Diet: {diet_type}
- Activity: {activity}
- Budget: {budget}
- Avoid: {allergies if allergies else 'nothing'}

For each day include: Breakfast, Morning Snack, Lunch, Evening Snack, Dinner, Post-workout (if applicable).
For each meal: name, ingredients, calories, protein/carbs/fat in grams.
Include daily totals and a short grocery list.
Where possible, use Indian foods that match the diet type.
Format clearly with headers."""
                        }],
                        max_tokens=2000
                    )
                    st.markdown(resp.choices[0].message.content)
                except Exception as e:
                    st.error(f"API Error: {e}")

# ── Tab 4: Nutrition Summary ───────────────────────────────────────────────────
with tabs[3]:
    today = get_today_calories()
    goal_cal = st.number_input("Daily calorie goal", 1200, 5000, 2000, step=100)

    st.subheader("📊 Today's Nutrition")
    cal_pct = min(today["calories"] / goal_cal, 1.0)
    color_bar = "normal" if cal_pct < 0.9 else "inverse"
    st.progress(cal_pct)
    st.caption(f"**{today['calories']:.0f}** / {goal_cal} kcal consumed")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Protein", f"{today['protein']:.0f}g", f"{max(0, 150-today['protein']):.0f}g left")
    m2.metric("Carbs", f"{today['carbs']:.0f}g", f"{max(0, 250-today['carbs']):.0f}g left")
    m3.metric("Fat", f"{today['fat']:.0f}g", f"{max(0, 65-today['fat']):.0f}g left")
    m4.metric("Fiber", f"{today['fiber']:.0f}g", f"{max(0, 25-today['fiber']):.0f}g left")

    nc1, nc2 = st.columns(2)
    with nc1:
        macro_vals = [today["protein"], today["carbs"], today["fat"]]
        if sum(macro_vals) > 0:
            macro_df = pd.DataFrame({"Macro": ["Protein", "Carbs", "Fat"], "Grams": macro_vals})
            fig = px.pie(macro_df, values="Grams", names="Macro",
                         color_discrete_sequence=["#1D9E75", "#378ADD", "#EF9F27"],
                         title="Macro Breakdown")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log meals to see macro breakdown")

    with nc2:
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=today["calories"],
            title={"text": "kcal today"},
            gauge={
                "axis": {"range": [0, goal_cal]},
                "bar": {"color": "#1D9E75"},
                "steps": [
                    {"range": [0, goal_cal * 0.5], "color": "#E1F5EE"},
                    {"range": [goal_cal * 0.5, goal_cal * 0.8], "color": "#9FE1CB"},
                    {"range": [goal_cal * 0.8, goal_cal], "color": "#5DCAA5"},
                ],
                "threshold": {"line": {"color": "red", "width": 3},
                              "thickness": 0.75, "value": goal_cal}
            }
        ))
        fig2.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

# ── Tab 5: Diet History ────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("📅 Meal History (Last 30 Days)")
    hist_df = get_diet_history(30)
    if not hist_df.empty:
        # Daily calorie trend
        daily = hist_df.groupby("date")["calories"].sum().reset_index()
        daily["date"] = pd.to_datetime(daily["date"])
        fig_hist = px.line(daily, x="date", y="calories",
                           title="Daily Calorie Intake",
                           color_discrete_sequence=["#1D9E75"])
        fig_hist.add_hline(y=2000, line_dash="dash",
                           annotation_text="2000 kcal goal",
                           line_color="rgba(200,100,100,0.5)")
        fig_hist.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", height=260)
        st.plotly_chart(fig_hist, use_container_width=True)

        # Meals by type
        type_counts = hist_df.groupby("meal_type")["calories"].sum().reset_index()
        fig_type = px.bar(type_counts, x="meal_type", y="calories",
                          title="Calories by Meal Type",
                          color_discrete_sequence=["#378ADD"])
        fig_type.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", height=220)
        st.plotly_chart(fig_type, use_container_width=True)

        st.subheader("Full Meal Log")
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("No meal history yet — start logging!")