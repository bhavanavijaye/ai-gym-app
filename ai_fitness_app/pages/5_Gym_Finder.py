import streamlit as st # pyright: ignore[reportMissingImports]
import requests # pyright: ignore[reportMissingModuleSource]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
import plotly.express as px # pyright: ignore[reportMissingImports]
from groq import Groq # pyright: ignore[reportMissingImports]
import os
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from utils.db import save_workout_program, get_saved_programs, get_program_by_id
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
load_dotenv()
from utils.sidebar import show_sidebar
st.set_page_config(page_title="Gym Finder & Programs", page_icon="📍", layout="wide")
st.title("📍 Gym Finder & Program Builder")
show_sidebar()
GROQ_MODEL = "llama-3.1-8b-instant"

tab_gym, tab_prog, tab_saved = st.tabs(["🔍 Find Gyms", "🤖 Build Program", "💾 Saved Programs"])

# ── Tab 1: Gym Finder ──────────────────────────────────────────────────────────
with tab_gym:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🔍 Find Gyms Near You")
        city = st.text_input("Enter your city", placeholder="Chennai, India",
                              value="Chennai")
        gym_type = st.multiselect(
            "Type of facility",
            ["Gym", "Yoga", "CrossFit", "Swimming", "Martial Arts"],
            default=["Gym"]
        )
        budget = st.select_slider(
            "Monthly Budget",
            options=["₹500", "₹1,000", "₹2,000", "₹3,000", "₹5,000", "₹10,000+"],
            value="₹3,000"
        )
        radius = st.slider("Search radius (km)", 1, 20, 5)

        if st.button("🔍 Search Gyms", type="primary", use_container_width=True):
            if not city.strip():
                st.warning("Please enter a city name")
            else:
                with st.spinner(f"Finding gyms in {city}..."):
                    query = f"""
                    [out:json];
                    area[name="{city}"]->.searchArea;
                    (
                      node["leisure"="fitness_centre"](area.searchArea);
                      node["sport"="gym"](area.searchArea);
                      node["leisure"="sports_centre"](area.searchArea);
                      node["leisure"="yoga"](area.searchArea);
                    );
                    out body 20;
                    """
                    try:
r = requests.post(
    "https://overpass-api.de/api/interpreter",
    data=query,
    timeout=25
)

if r.status_code != 200:
    st.error("Gym API failed. Try again later.")
    st.stop()

if not r.text.strip():
    st.error("No response from gym server.")
    st.stop()

try:
    data = r.json()
except Exception:
    st.error("Invalid response from gym API.")
    st.text(r.text[:300])
    st.stop()
                        gyms = []
                        for el in data.get("elements", []):
                            tags = el.get("tags", {})
                            name = tags.get("name", "").strip()
                            if not name:
                                continue
                            gyms.append({
                                "Name": name,
                                "Type": tags.get("sport", tags.get("leisure", "Fitness")).title(),
                                "Address": tags.get("addr:street", "—"),
                                "Phone": tags.get("phone", "—"),
                                "Website": tags.get("website", "—"),
                                "Opening": tags.get("opening_hours", "—"),
                                "Lat": el.get("lat"),
                                "Lon": el.get("lon")
                            })

                        if gyms:
                            df = pd.DataFrame(gyms)
                            st.success(f"Found {len(df)} facilities in {city}")
                            st.dataframe(
                                df[["Name", "Type", "Address", "Phone", "Opening"]],
                                use_container_width=True, hide_index=True
                            )
                            valid_map = df.dropna(subset=["Lat", "Lon"])
                            if not valid_map.empty:
                                fig = px.scatter_mapbox(
                                    valid_map, lat="Lat", lon="Lon",
                                    hover_name="Name",
                                    hover_data=["Type", "Address", "Phone"],
                                    zoom=12, mapbox_style="open-street-map",
                                    title=f"Gyms in {city}",
                                    color_discrete_sequence=["#1D9E75"],
                                    size_max=15
                                )
                                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)")
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"No gyms found in '{city}'. Try a larger city name.")
                            st.info("Tip: Try 'Chennai' instead of 'Chennai, India'")
                    except requests.exceptions.Timeout:
                        st.error("Search timed out. Please try again.")
                    except Exception as e:
                        st.error(f"Search failed: {e}")

    with col2:
        st.subheader("📊 Gym Type Distribution")
        if "df" in dir() and not df.empty:
            type_counts = df["Type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            fig_tc = px.pie(type_counts, values="Count", names="Type",
                            color_discrete_sequence=["#1D9E75", "#378ADD", "#EF9F27",
                                                      "#E24B4A", "#9B59B6"])
            fig_tc.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("Search for gyms to see distribution")

        st.divider()
        st.subheader("💰 Gym Budget Guide (Chennai)")
        budget_data = pd.DataFrame({
            "Type": ["Budget Gym", "Mid-range", "Premium", "CrossFit Box", "Boutique Studio"],
            "Price Range": ["₹500–1,000/mo", "₹1,500–2,500/mo", "₹3,000–5,000/mo",
                            "₹3,000–6,000/mo", "₹4,000–8,000/mo"],
            "What to Expect": [
                "Basic equipment, no AC",
                "Good equipment, AC, some classes",
                "Full equipment, pool, sauna, classes",
                "Olympic lifting, coaching, community",
                "Yoga, pilates, personal training focus"
            ]
        })
        st.dataframe(budget_data, use_container_width=True, hide_index=True)

# ── Tab 2: Program Builder ─────────────────────────────────────────────────────
with tab_prog:
    st.subheader("🤖 AI Workout Program Builder")

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        fitness_level = st.selectbox("Fitness Level",
                                      ["Beginner", "Intermediate", "Advanced", "Athlete"])
        days_per_week = st.slider("Days per week", 2, 6, 4)
        program_duration = st.selectbox("Program duration",
                                         ["4 weeks", "8 weeks", "12 weeks"])
    with pc2:
        duration = st.selectbox("Session Duration",
                                 ["30 minutes", "45 minutes", "60 minutes", "90 minutes"])
        location = st.selectbox("Training Location", ["Gym", "Home", "Outdoors", "Mixed"])
        program_style = st.selectbox("Program Style",
                                      ["PPL (Push/Pull/Legs)", "Full Body",
                                       "Upper/Lower Split", "Bro Split",
                                       "Athletic Performance", "Custom"])
    with pc3:
        focus = st.multiselect(
            "Focus Areas",
            ["Strength", "Hypertrophy", "Cardio", "Flexibility", "Weight Loss",
             "Muscle Gain", "Core", "Endurance", "Power", "Mobility"],
            default=["Strength", "Hypertrophy"]
        )
        equipment = st.text_input("Equipment available",
                                   placeholder="e.g. barbells, dumbbells, cables")
        injuries = st.text_input("Any injuries / limitations",
                                  placeholder="e.g. bad knees, shoulder injury")

    program_name = st.text_input("Program name (for saving)",
                                  placeholder="e.g. My 12-Week Bulk Program")

    col_gen, col_save = st.columns([2, 1])
    with col_gen:
        generate = st.button("🏋️ Generate My Program", type="primary", use_container_width=True)

    if generate:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY not found")
        elif not focus:
            st.warning("Select at least one focus area")
        else:
            with st.spinner("Building your personalized program..."):
                try:
                    client = Groq(api_key=api_key)
                    resp = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{
                            "role": "user",
                            "content": f"""Create a detailed {program_duration}, {days_per_week}-day/week workout program:

- Level: {fitness_level}
- Style: {program_style}
- Location: {location}
- Duration: {duration}/session
- Focus: {', '.join(focus)}
- Equipment: {equipment if equipment else 'standard gym'}
- Limitations: {injuries if injuries else 'none'}

Format as:
## Week Structure
## Day-by-Day Schedule (full week)
For each day: Muscle Group | Exercise | Sets x Reps | Rest | Form Tip

## Progression Scheme (how to progress each week)
## Warm-up Protocol (5 min)
## Cool-down Protocol (5 min)
## Recovery & Nutrition Tips

Make it practical and specific. Include rest days."""
                        }],
                        max_tokens=2000
                    )
                    program_content = resp.choices[0].message.content
                    st.session_state["last_program"] = program_content
                    st.session_state["last_program_level"] = fitness_level
                    st.session_state["last_program_days"] = days_per_week
                    st.markdown(program_content)

                    # Save button after generation
                    if st.button("💾 Save This Program", type="secondary",
                                  use_container_width=True):
                        name = program_name.strip() or f"{fitness_level} {program_style} Program"
                        save_workout_program(name, program_content, fitness_level, days_per_week)
                        st.success(f"✅ Saved: '{name}'")

                except Exception as e:
                    st.error(f"API Error: {e}")

    # Fitness goal calculator
    st.divider()
    st.subheader("📊 Fitness Goal Calculator")
    gc1, gc2 = st.columns(2)
    with gc1:
        curr_weight = st.number_input("Current Weight (kg)", 40.0, 200.0, 70.0)
        target_weight = st.number_input("Target Weight (kg)", 40.0, 200.0, 65.0)
    with gc2:
        weeks = st.number_input("Timeline (weeks)", 1, 52, 12)
        activity_level = st.selectbox("Activity Level",
                                       ["Sedentary", "Lightly Active",
                                        "Moderately Active", "Very Active"])

    if st.button("📈 Calculate Plan", use_container_width=True):
        diff = curr_weight - target_weight
        weekly_change = diff / weeks if weeks > 0 else 0
        cal_deficit = weekly_change * 7700 / 7

        if abs(weekly_change) > 1:
            st.warning(f"⚠️ {abs(weekly_change):.1f}kg/week is aggressive. Max: 0.5–1kg/week.")
        else:
            st.success(f"✅ Realistic goal: {abs(weekly_change):.2f}kg/week")

        direction = "deficit" if diff > 0 else "surplus"
        st.info(f"""
**Your Plan:**
- Weekly change: **{abs(weekly_change):.2f}kg/week**
- Daily calorie {direction}: **{abs(cal_deficit):.0f} kcal/day**
- Total change: **{abs(diff):.1f}kg** over **{weeks} weeks**
- Estimated completion: around week {weeks}
        """)

# ── Tab 3: Saved Programs ──────────────────────────────────────────────────────
with tab_saved:
    st.subheader("💾 Your Saved Programs")
    saved_df = get_saved_programs()
    if saved_df.empty:
        st.info("No saved programs yet. Generate a program and save it!")
    else:
        for _, row in saved_df.iterrows():
            with st.expander(
                f"🏋️ {row['name']} — {row['level']} · {row['days_per_week']} days/week · "
                f"Saved {row['created_date']}"
            ):
                prog = get_program_by_id(row["id"])
                if prog:
                    st.markdown(prog[3])  # program_text column
                    st.download_button(
                        "⬇️ Download",
                        data=prog[3],
                        file_name=f"{row['name'].replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"dl_{row['id']}"
                    )
