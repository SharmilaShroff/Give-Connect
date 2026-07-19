import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.utils.session import require_login
from frontend.utils.navigation import render_sidebar
from backend import admin_dashboard as api

st.set_page_config(page_title="User Moderation - Admin Portal", page_icon="👥", layout="wide")

user = require_login()
if user["account_type"] != "admin":
    st.error("Unauthorized Access")
    st.stop()

render_sidebar()

st.title("👥 User Moderation")

search_query = st.text_input("Search Users (by ID, Name, or Email)")

users = api.get_all_users(user["user_id"], search_query)

if not users:
    st.info("No users found.")
else:
    for u in users:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{u['full_name']}** (@{u['user_id']})")
                st.write(f"Email: `{u['email']}` | Type: `{u['account_type']}`")
                st.write(f"Posts: {u['post_count']} | Reports Against: {u['reports_against']}")
                if u['is_blocked']:
                    st.error("Account is currently BLOCKED.")
            with col2:
                if u['account_type'] != 'admin':
                    confirm_key = f"confirm_del_{u['user_id']}"
                    if st.checkbox("Confirm Deletion", key=confirm_key):
                        if st.button("🗑️ Delete User", type="primary", key=f"del_{u['user_id']}"):
                            api.delete_user(user["user_id"], u['user_id'])
                            st.success(f"User {u['user_id']} completely removed.")
                            st.rerun()
