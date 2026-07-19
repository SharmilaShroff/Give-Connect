import streamlit as st


def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None


def current_user():
    return st.session_state.get("user")


def require_login():
    """Call at the top of every protected page. Halts rendering with a friendly
    message + link back to Home if nobody is logged in."""
    init_session()
    if not st.session_state.user:
        st.warning("Please log in first.")
        st.page_link("Home.py", label="Go to Login", icon="🔑")
        st.stop()
    return st.session_state.user


def logout():
    st.session_state.user = None
