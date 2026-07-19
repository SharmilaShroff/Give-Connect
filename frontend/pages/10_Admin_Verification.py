import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.utils.session import require_login
from frontend.utils.navigation import render_sidebar
from backend import admin_dashboard as api
from backend import verification as verify_api

st.set_page_config(page_title="NGO Verification - Admin Portal", page_icon="✅", layout="wide")

user = require_login()
if user["account_type"] != "admin":
    st.error("Unauthorized Access")
    st.stop()

render_sidebar()

st.title("✅ NGO Verification Queue")

ngos = api.get_ngos(user["user_id"])

st.markdown("Review and verify registered NGOs. The Blue Verification Badge can only be granted here.")

for n in ngos:
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"{n['full_name']} (@{n['user_id']})")
            st.write(f"Email: {n['email']}")
            if n.get('registration_number'):
                st.write(f"**Registration:** {n['registration_number']}")
                
                with st.expander("Bank Details"):
                    st.write(f"**Bank Name:** {n.get('bank_name') or 'N/A'}")
                    st.write(f"**Account Holder:** {n.get('account_holder_name') or 'N/A'}")
                    st.write(f"**Account Number:** {n.get('bank_account_number') or 'N/A'}")
                    st.write(f"**IFSC Code:** {n.get('bank_ifsc') or 'N/A'}")

                doc_path = n.get('legal_verification_doc')
                if doc_path and os.path.exists(doc_path):
                    try:
                        with open(doc_path, "rb") as f:
                            file_data = f.read()
                        file_name = os.path.basename(doc_path)
                        st.download_button(
                            label="📄 Download Verification Document",
                            data=file_data,
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"dl_{n['user_id']}"
                        )
                    except Exception as e:
                        st.error(f"Error reading document: {e}")
                else:
                    st.write(f"**Document Path:** `{doc_path}` (File not found on disk)")
            else:
                st.warning("No registration details submitted yet.")
            
            if n['is_verified']:
                st.success("STATUS: VERIFIED 🔵")
            else:
                st.warning("STATUS: UNVERIFIED")
                
        with col2:
            st.write("**Admin Actions**")
            if not n['is_verified']:
                if st.button("Grant Verification", type="primary", key=f"verify_{n['user_id']}"):
                    verify_api.grant_verification(user["user_id"], n['user_id'])
                    st.success("Verification granted.")
                    st.rerun()
            else:
                if st.button("Revoke Verification", key=f"revoke_{n['user_id']}"):
                    verify_api.revoke_verification(user["user_id"], n['user_id'])
                    st.success("Verification revoked.")
                    st.rerun()
