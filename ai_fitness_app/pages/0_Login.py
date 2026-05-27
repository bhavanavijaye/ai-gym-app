import streamlit as st # pyright: ignore[reportMissingImports]

from utils.db import create_user, login_user
from utils.db import (
    create_user,
    login_user,
    init_db
)


init_db()
st.set_page_config(page_title="Login")

st.title("💪 AI Fitness Login")

menu = st.selectbox(
    "Choose",
    ["Login", "Signup"]
)

email = st.text_input("Email")

password = st.text_input(
    "Password",
    type="password"
)

# SIGNUP
if menu == "Signup":

    if st.button("Create Account"):

        success = create_user(
            email,
            password
        )

        if success:
            st.success("Account created!")

        else:
            st.error("User already exists")


# LOGIN
else:

    if st.button("Login"):

        valid = login_user(
            email,
            password
        )

        if valid:

            st.session_state["logged_in"] = True
            st.session_state["user_email"] = email

            st.success("Login successful!")

            st.switch_page("app.py")

        else:
            st.error("Invalid email or password")