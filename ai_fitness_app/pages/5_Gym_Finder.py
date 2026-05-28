import streamlit as st  # pyright: ignore[reportMissingImports]
import requests
import pandas as pd
import plotly.express as px
from groq import Groq
import os
from dotenv import load_dotenv
from utils.db import (
    save_workout_program,
    get_saved_programs,
    get_program_by_id
)
from utils.sidebar import show_sidebar

# ─────────────────────────────────────────────────────────────
# LOGIN CHECK
# ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
load_dotenv()

st.set_page_config(
    page_title="Gym Finder & Programs",
    page_icon="📍",
    layout="wide"
)

show_sidebar()

st.title("📍 Gym Finder & Program Builder")

GROQ_MODEL = "llama-3.1-8b-instant"

tab_gym, tab_prog, tab_saved = st.tabs([
    "🔍 Find Gyms",
    "🤖 Build Program",
    "💾 Saved Programs"
])

# ============================================================
# TAB 1 — GYM FINDER
# ============================================================
with tab_gym:

    col1, col2 = st.columns([1, 1])

    with col1:

        st.subheader("🔍 Find Gyms Near You")

        city = st.text_input(
            "Enter your city",
            value="Chennai"
        )

        gym_type = st.multiselect(
            "Type of facility",
            ["Gym", "Yoga", "CrossFit", "Swimming", "Martial Arts"],
            default=["Gym"]
        )

        budget = st.select_slider(
            "Monthly Budget",
            options=[
                "₹500",
                "₹1,000",
                "₹2,000",
                "₹3,000",
                "₹5,000",
                "₹10,000+"
            ],
            value="₹3,000"
        )

        radius = st.slider(
            "Search radius (km)",
            1,
            20,
            5
        )

        gyms = []
        df = pd.DataFrame()

        if st.button(
            "🔍 Search Gyms",
            type="primary",
            use_container_width=True
        ):

            if not city.strip():
                st.warning("Please enter a city name")

            else:

                with st.spinner(f"Searching gyms in {city}..."):

                    query = f"""
                    [out:json];
                    area[name="{city}"]->.searchArea;
                    (
                      node["leisure"="fitness_centre"](area.searchArea);
                      node["sport"="gym"](area.searchArea);
                      node["leisure"="sports_centre"](area.searchArea);
                    );
                    out body;
                    """

                    try:

                        r = requests.post(
                            "https://overpass-api.de/api/interpreter",
                            data=query,
                            timeout=30
                        )

                        if r.status_code != 200:
                            st.error("Gym API failed.")
                            st.stop()

                        data = r.json()

                        for el in data.get("elements", []):

                            tags = el.get("tags", {})

                            name = tags.get("name", "Unknown Gym")

                            gyms.append({
                                "Name": name,
                                "Type": tags.get(
                                    "sport",
                                    tags.get("leisure", "Gym")
                                ),
                                "Address": tags.get(
                                    "addr:street",
                                    "Not Available"
                                ),
                                "Phone": tags.get(
                                    "phone",
                                    "Not Available"
                                ),
                                "Opening": tags.get(
                                    "opening_hours",
                                    "Not Available"
                                ),
                                "Lat": el.get("lat"),
                                "Lon": el.get("lon")
                            })

                        if gyms:

                            df = pd.DataFrame(gyms)

                            st.success(
                                f"Found {len(df)} gyms in {city}"
                            )

                            st.dataframe(
                                df[
                                    [
                                        "Name",
                                        "Type",
                                        "Address",
                                        "Phone",
                                        "Opening"
                                    ]
                                ],
                                use_container_width=True,
                                hide_index=True
                            )

                            valid_map = df.dropna(
                                subset=["Lat", "Lon"]
                            )

                            if not valid_map.empty:

                                fig = px.scatter_mapbox(
                                    valid_map,
                                    lat="Lat",
                                    lon="Lon",
                                    hover_name="Name",
                                    hover_data=[
                                        "Type",
                                        "Address"
                                    ],
                                    zoom=11,
                                    mapbox_style="open-street-map",
                                    height=450
                                )

                                st.plotly_chart(
                                    fig,
                                    use_container_width=True
                                )

                        else:
                            st.warning(
                                f"No gyms found in {city}"
                            )

                    except requests.exceptions.Timeout:
                        st.error("Request timed out")

                    except Exception as e:
                        st.error(f"Search failed: {e}")

    # ========================================================
    # RIGHT SIDE
    # ========================================================
    with col2:

        st.subheader("📊 Gym Type Distribution")

        if not df.empty:

            type_counts = (
                df["Type"]
                .value_counts()
                .reset_index()
            )

            type_counts.columns = ["Type", "Count"]

            fig_pie = px.pie(
                type_counts,
                values="Count",
                names="Type"
            )

            st.plotly_chart(
                fig_pie,
                use_container_width=True
            )

        else:
            st.info("Search gyms to see analytics")

        st.divider()

        st.subheader("💰 Budget Guide")

        budget_df = pd.DataFrame({
            "Type": [
                "Budget Gym",
                "Mid-range Gym",
                "Premium Gym"
            ],
            "Price": [
                "₹500–1000",
                "₹1500–3000",
                "₹4000+"
            ]
        })

        st.dataframe(
            budget_df,
            use_container_width=True,
            hide_index=True
        )

# ============================================================
# TAB 2 — AI PROGRAM BUILDER
# ============================================================
with tab_prog:

    st.subheader("🤖 AI Workout Program Builder")

    fitness_level = st.selectbox(
        "Fitness Level",
        ["Beginner", "Intermediate", "Advanced"]
    )

    days_per_week = st.slider(
        "Days per week",
        2,
        6,
        4
    )

    goal = st.multiselect(
        "Goals",
        [
            "Muscle Gain",
            "Weight Loss",
            "Strength",
            "Cardio"
        ],
        default=["Muscle Gain"]
    )

    program_name = st.text_input(
        "Program Name"
    )

    if st.button(
        "🏋️ Generate My Program",
        type="primary"
    ):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            st.error("GROQ_API_KEY missing")

        else:

            try:

                client = Groq(api_key=api_key)

                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""
Create a {days_per_week}-day workout plan.

Fitness Level: {fitness_level}
Goals: {", ".join(goal)}

Include:
- exercises
- sets
- reps
- rest
- tips
"""
                        }
                    ],
                    max_tokens=1500
                )

                content = response.choices[0].message.content

                st.markdown(content)

                if st.button("💾 Save Program"):

                    name = (
                        program_name.strip()
                        or "Workout Program"
                    )

                    save_workout_program(
                        name,
                        content,
                        fitness_level,
                        days_per_week
                    )

                    st.success("Program Saved")

            except Exception as e:
                st.error(f"AI Error: {e}")

# ============================================================
# TAB 3 — SAVED PROGRAMS
# ============================================================
with tab_saved:

    st.subheader("💾 Saved Programs")

    saved_df = get_saved_programs()

    if saved_df.empty:

        st.info("No saved programs")

    else:

        for _, row in saved_df.iterrows():

            with st.expander(
                f"{row['name']} — {row['level']}"
            ):

                prog = get_program_by_id(row["id"])

                if prog:

                    st.markdown(prog[3])

                    st.download_button(
                        "⬇️ Download",
                        data=prog[3],
                        file_name=f"{row['name']}.txt",
                        mime="text/plain",
                        key=f"dl_{row['id']}"
                    )
