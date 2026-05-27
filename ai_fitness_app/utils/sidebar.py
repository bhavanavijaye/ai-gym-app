import streamlit as st # pyright: ignore[reportMissingImports]

def show_sidebar():

    with st.sidebar:

        st.markdown("## 💪 AI Fitness OS")

        st.markdown("### Navigation")

        if st.button("🏠 Dashboard", use_container_width=True):
            st.switch_page("app.py")

        if st.button("🏋 Workout Trainer", use_container_width=True):
            st.switch_page("pages/1_Workout_Trainer.py")

        if st.button("🥗 Diet Coach", use_container_width=True):
            st.switch_page("pages/2_Diet_Coach.py")

        if st.button("🤖 AI Coach", use_container_width=True):
            st.switch_page("pages/3_AI_Chatbot.py")

        if st.button("📊 Habit Tracker", use_container_width=True):
            st.switch_page("pages/4_Habit_Tracker.py")

        if st.button("📏 Body Stats", use_container_width=True):
            st.switch_page("pages/6_Body_Stats.py")

        if st.button("📅 Weekly Report", use_container_width=True):
            st.switch_page("pages/7_Weekly_Report.py")

        st.markdown("---")

        st.success(
            f"👤 {st.session_state.get('user_email', 'Guest User')}"
        )

        if st.button("Logout", use_container_width=True):

            st.session_state.clear()

            st.switch_page("pages/0_Login.py")
