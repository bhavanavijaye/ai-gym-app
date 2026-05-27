import streamlit as st # pyright: ignore[reportMissingImports]
import plotly.express as px # pyright: ignore[reportMissingImports]
import plotly.graph_objects as go # pyright: ignore[reportMissingImports]
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from datetime import date
from utils.db import (
    log_body_stats, get_body_stats_history, get_latest_body_stats
)
if "logged_in" not in st.session_state:
    st.switch_page("pages/0_Login.py")
st.set_page_config(page_title="Body Stats", page_icon="📏", layout="wide")
st.title("📏 Body Stats & Progress Tracker")
st.markdown("Track weight, body measurements, BMI and body composition over time")
from utils.sidebar import show_sidebar
col1, col2 = st.columns([1, 2])
show_sidebar()
# ── Left: log stats ────────────────────────────────────────────────────────────
with col1:
    st.subheader("📝 Log Today's Stats")

    latest = get_latest_body_stats()

    # Pre-fill with last values
    last_weight = latest["weight_kg"] if latest else 70.0
    last_fat = latest["body_fat_pct"] if latest else 0.0

    weight_kg = st.number_input("Weight (kg)", 30.0, 250.0, last_weight, step=0.1)
    body_fat = st.number_input("Body Fat % (optional)", 0.0, 60.0, last_fat, step=0.1,
                                help="Use a body fat scale or tape measure estimate")

    st.subheader("📐 Measurements (cm) — optional")
    mc1, mc2 = st.columns(2)
    with mc1:
        chest = st.number_input("Chest", 0.0, 200.0,
                                 latest["chest_cm"] if latest else 0.0, step=0.5)
        waist = st.number_input("Waist", 0.0, 200.0,
                                 latest["waist_cm"] if latest else 0.0, step=0.5)
        hips = st.number_input("Hips", 0.0, 200.0,
                                latest["hips_cm"] if latest else 0.0, step=0.5)
    with mc2:
        bicep = st.number_input("Bicep", 0.0, 80.0,
                                 latest["bicep_cm"] if latest else 0.0, step=0.5)
        thigh = st.number_input("Thigh", 0.0, 120.0,
                                 latest["thigh_cm"] if latest else 0.0, step=0.5)

    notes = st.text_area("Notes", placeholder="e.g. Morning weight, after cardio...", height=60)

    if st.button("💾 Save Stats", type="primary", use_container_width=True):
        log_body_stats(weight_kg, body_fat, chest, waist, hips, bicep, thigh, notes)
        st.success(f"✅ Stats saved — {weight_kg}kg logged!")
        st.rerun()

    st.divider()
    st.subheader("🔢 BMI Calculator")
    height_cm = st.number_input("Your height (cm)", 140, 220, 170)
    if height_cm > 0:
        bmi = weight_kg / ((height_cm / 100) ** 2)
        if bmi < 18.5:
            bmi_cat, bmi_color = "Underweight", "#378ADD"
        elif bmi < 25:
            bmi_cat, bmi_color = "Normal", "#1D9E75"
        elif bmi < 30:
            bmi_cat, bmi_color = "Overweight", "#EF9F27"
        else:
            bmi_cat, bmi_color = "Obese", "#E24B4A"

        fig_bmi = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=bmi,
            title={"text": f"BMI — {bmi_cat}"},
            delta={"reference": 22.5, "valueformat": ".1f"},
            number={"valueformat": ".1f"},
            gauge={
                "axis": {"range": [10, 40]},
                "bar": {"color": bmi_color},
                "steps": [
                    {"range": [10, 18.5], "color": "#BDD9F5"},
                    {"range": [18.5, 25], "color": "#E1F5EE"},
                    {"range": [25, 30], "color": "#FFF3CD"},
                    {"range": [30, 40], "color": "#FFE0DE"},
                ],
                "threshold": {"line": {"color": "white", "width": 2},
                              "thickness": 0.75, "value": 22.5}
            }
        ))
        fig_bmi.update_layout(height=260, paper_bgcolor="rgba(0,0,0,0)",
                              margin=dict(t=20, b=0))
        st.plotly_chart(fig_bmi, use_container_width=True)

# ── Right: history charts ──────────────────────────────────────────────────────
with col2:
    df = get_body_stats_history()

    if df.empty:
        st.info("No body stats logged yet. Use the form on the left to start tracking!")
    else:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        tab_w, tab_m, tab_f, tab_raw = st.tabs([
            "⚖️ Weight Trend", "📐 Measurements", "💧 Body Fat", "📋 Raw Data"
        ])

        with tab_w:
            # Weight trend with 7-day rolling average
            df["weight_7d"] = df["weight_kg"].rolling(7, min_periods=1).mean()

            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(
                x=df["date"], y=df["weight_kg"],
                mode="lines+markers", name="Daily Weight",
                line=dict(color="#378ADD", width=1.5),
                marker=dict(size=5)
            ))
            fig_w.add_trace(go.Scatter(
                x=df["date"], y=df["weight_7d"],
                mode="lines", name="7-Day Avg",
                line=dict(color="#1D9E75", width=2.5, dash="dash")
            ))

            # Weight change annotation
            if len(df) >= 2:
                change = df["weight_kg"].iloc[-1] - df["weight_kg"].iloc[0]
                change_str = f"{'▼' if change < 0 else '▲'} {abs(change):.1f}kg since start"
                fig_w.add_annotation(
                    x=df["date"].iloc[-1], y=df["weight_kg"].iloc[-1],
                    text=change_str,
                    showarrow=True, arrowhead=2,
                    font=dict(color="#1D9E75" if change <= 0 else "#EF9F27")
                )

            fig_w.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=340, yaxis_title="Weight (kg)",
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_w, use_container_width=True)

            # Stats row
            if len(df) >= 2:
                total_change = df["weight_kg"].iloc[-1] - df["weight_kg"].iloc[0]
                max_w = df["weight_kg"].max()
                min_w = df["weight_kg"].min()
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Current", f"{df['weight_kg'].iloc[-1]:.1f}kg")
                s2.metric("Change", f"{total_change:+.1f}kg")
                s3.metric("Highest", f"{max_w:.1f}kg")
                s4.metric("Lowest", f"{min_w:.1f}kg")

        with tab_m:
            measures = {
                "chest_cm": "Chest", "waist_cm": "Waist",
                "hips_cm": "Hips", "bicep_cm": "Bicep", "thigh_cm": "Thigh"
            }
            available = {k: v for k, v in measures.items()
                         if k in df.columns and df[k].sum() > 0}

            if available:
                selected_m = st.multiselect(
                    "Show measurements",
                    list(available.values()),
                    default=list(available.values())[:3]
                )
                reverse_m = {v: k for k, v in available.items()}
                cols_to_show = [reverse_m[m] for m in selected_m if m in reverse_m]

                if cols_to_show:
                    fig_m = px.line(df, x="date", y=cols_to_show,
                                    labels={k: v for k, v in measures.items()},
                                    color_discrete_sequence=["#1D9E75", "#378ADD",
                                                              "#EF9F27", "#E24B4A", "#9B59B6"])
                    fig_m.update_traces(mode="lines+markers")
                    fig_m.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        height=340, yaxis_title="Centimeters"
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
            else:
                st.info("Enter measurements (chest, waist, etc.) when logging stats to see trends.")

        with tab_f:
            if "body_fat_pct" in df.columns and df["body_fat_pct"].sum() > 0:
                fig_f = px.area(df, x="date", y="body_fat_pct",
                                color_discrete_sequence=["#EF9F27"],
                                title="Body Fat % Over Time")
                # Reference lines
                fig_f.add_hline(y=15, line_dash="dash",
                                annotation_text="Athletic (15%)",
                                line_color="rgba(29,158,117,0.5)")
                fig_f.add_hline(y=25, line_dash="dash",
                                annotation_text="Average (25%)",
                                line_color="rgba(239,159,39,0.5)")
                fig_f.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=340
                )
                st.plotly_chart(fig_f, use_container_width=True)
            else:
                st.info("Log body fat % when adding stats to track body composition.")

        with tab_raw:
            display_df = df.copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(display_df.drop(columns=["id"], errors="ignore"),
                         use_container_width=True, hide_index=True)

            # Export
            csv = display_df.to_csv(index=False)
            st.download_button(
                "⬇️ Download as CSV",
                data=csv,
                file_name=f"body_stats_{date.today()}.csv",
                mime="text/csv"
            )