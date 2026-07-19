import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.utils.session import require_login
from frontend.utils.navigation import render_sidebar
from backend import admin_dashboard as api

st.set_page_config(page_title="Reported Posts - Admin Portal", page_icon="🚨", layout="wide")

user = require_login()
if user["account_type"] != "admin":
    st.error("Unauthorized Access")
    st.stop()

render_sidebar()

st.title("🚨 Reported Posts Management")

reports = api.get_all_reports(user["user_id"])

if not reports:
    st.success("No active reports! The community is clean.")
else:
    for r in reports:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"Post #{r['post_id']} by @{r['poster_id']} ({r['poster_name']})")
                st.markdown(f"**Report Reason:** `{r['reason']}`")
                if r.get('details'):
                    st.write(f"**Additional Details:** {r['details']}")
                st.write(f"**Reported By:** {r['reporter_name']}")
                st.markdown("---")
                st.write(r['caption'])
                if r.get('image_path') and os.path.exists(r['image_path']):
                    st.image(r['image_path'], width=300)
            
            with col2:
                st.write("**Admin Actions**")
                if st.button("Ignore Report", key=f"ignore_{r['report_id']}"):
                    api.ignore_report(user["user_id"], r['report_id'])
                    st.rerun()
                
                if st.button("🗑️ Delete Post", type="primary", key=f"delete_post_{r['report_id']}"):
                    api.delete_post(user["user_id"], r['post_id'])
                    st.success("Post deleted.")
                    st.rerun()
                
                if st.button("⛔ Suspend User", key=f"suspend_user_{r['report_id']}"):
                    from database.db import run_update
                    run_update("UPDATE users SET is_blocked=TRUE WHERE user_id=%s", (r['poster_id'],))
                    st.success("User blocked.")
                    st.rerun()
