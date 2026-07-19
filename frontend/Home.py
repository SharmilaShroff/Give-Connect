import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from backend import auth
from backend.file_utils import save_upload
from backend.scheduler import start_scheduler
from frontend.utils.session import init_session

st.set_page_config(page_title="GiveConnect - Login", page_icon="🤝", layout="centered")
init_session()
start_scheduler()  # auto-delete-expired-#food-posts job; guarded to run once per process

# Hide sidebar on login page
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if st.session_state.user:
    st.switch_page("pages/1_Feed.py")
    st.stop()

st.title("🤝 GiveConnect")

tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

# ------------------------------------------------------------------ LOGIN
with tab_login:
    st.subheader("Log in")
    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)
    if submitted:
        try:
            user = auth.login(user_id.strip(), password)
            if user:
                st.session_state.user = user
                if user["account_type"] == "admin":
                    st.switch_page("pages/7_Admin_Dashboard.py")
                else:
                    st.switch_page("pages/1_Feed.py")
            else:
                st.error("Invalid user ID or password.")
        except PermissionError as e:
            st.error(str(e))

# ------------------------------------------------------------------ CREATE ACCOUNT
with tab_signup:
    st.subheader("Create account")
    account_type = st.radio("Register as", ["Individual", "NGO"], horizontal=True)

    if account_type == "Individual":
        with st.form("individual_signup"):
            new_user_id = st.text_input("Choose a User ID")
            new_password = st.text_input("Choose a Password", type="password")
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            interests = st.text_input("Interests / preferences (comma-separated, e.g. food, education, animals)")
            submitted = st.form_submit_button("Create Individual Account", use_container_width=True)
        if submitted:
            try:
                auth.register_individual(
                    new_user_id.strip(), new_password, email.strip(), full_name.strip(),
                    [i.strip() for i in interests.split(",")],
                )
                st.success("Account created! Please log in from the 'Log In' tab.")
            except ValueError as e:
                st.error(str(e))

    else:  # NGO
        with st.form("ngo_signup"):
            st.markdown("**Login credentials**")
            new_user_id = st.text_input("Choose a User ID")
            new_password = st.text_input("Choose a Password", type="password")
            st.markdown("**NGO details**")
            ngo_name = st.text_input("NGO legal name")
            email = st.text_input("Official email")
            registration_number = st.text_input("NGO registration number")
            legal_doc = st.file_uploader("Legal verification document (registration cert / 80G / 12A etc.)",
                                          type=["pdf", "png", "jpg", "jpeg"])
            st.markdown("**Bank details** (for receiving donations)")
            account_holder_name = st.text_input("Account holder name *")
            bank_account_number = st.text_input("Bank account number *")
            bank_ifsc = st.text_input("IFSC / routing code *")
            bank_name = st.text_input("Bank name *")
            submitted = st.form_submit_button("Submit NGO Registration", use_container_width=True)
        if submitted:
            if not legal_doc:
                st.error("Legal verification document is required.")
            else:
                try:
                    doc_path = save_upload(legal_doc, "ngo_docs")
                    auth.register_ngo(
                        new_user_id.strip(), new_password, email.strip(), ngo_name.strip(),
                        registration_number.strip(), doc_path, bank_account_number.strip(),
                        bank_ifsc.strip(), bank_name.strip(), account_holder_name.strip(),
                    )
                    st.success(
                        "NGO account created and submitted for review. You can log in now; "
                        "the verified blue-tick badge is granted separately by platform authority "
                        "once your documents are reviewed."
                    )
                except ValueError as e:
                    st.error(str(e))
