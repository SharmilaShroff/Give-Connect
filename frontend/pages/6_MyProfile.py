import streamlit as st
from frontend.utils.session import require_login

user = require_login()

st.session_state.viewing_profile = user["user_id"]
st.session_state.profile_history = []
st.switch_page("pages/2_Profile.py")
