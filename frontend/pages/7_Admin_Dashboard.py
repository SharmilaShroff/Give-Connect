import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.utils.session import require_login
from frontend.utils.navigation import render_sidebar
from backend import admin_dashboard as api

st.set_page_config(page_title="Dashboard - Admin Portal", page_icon="📊", layout="wide")

user = require_login()
if user["account_type"] != "admin":
    st.error("Unauthorized Access")
    st.stop()

render_sidebar()

st.title("📊 Platform Dashboard")

metrics = api.get_dashboard_metrics(user["user_id"])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Users", metrics["total_users"])
col2.metric("Total Posts", metrics["total_posts"])
col3.metric("Total NGOs", metrics["total_ngos"])
col4.metric("Reported Posts", metrics["total_reports"])
col5.metric("Verified NGOs", metrics["total_verified_ngos"])

st.markdown("---")
st.subheader("Recent Reports")
if not metrics["recent_reports"]:
    st.info("No recent reports.")
else:
    for r in metrics["recent_reports"]:
        with st.container(border=True):
            st.markdown(f"**Reported Post**: {r['caption']}")
            st.caption(f"Reported by: @{r['reporter_name']} • Poster: @{r['poster_id']} • Reason: {r['reason']}")
            st.write(f"Details: {r['details']}")
