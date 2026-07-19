import frontend.utils.bootstrap  # noqa: F401
import streamlit as st

from backend import posts as posts_backend
from backend.file_utils import save_upload
from frontend.utils.session import require_login

st.set_page_config(page_title="Create Post - GiveConnect", page_icon="➕", layout="centered")
user = require_login()

from frontend.utils.navigation import render_sidebar, render_chatbot
render_sidebar()
render_chatbot()

st.title("➕ Create a Post")
st.caption("📍 Location and at least one #hashtag are required for every post.")

if "post_success_msg" in st.session_state:
    st.success(st.session_state.post_success_msg)
    del st.session_state.post_success_msg

if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

image = st.file_uploader("Photo (required, auto-cropped to 1:1)", type=["png", "jpg", "jpeg"], key=f"post_image_{st.session_state.upload_key}")

with st.form("create_post_form", clear_on_submit=True):
    caption = st.text_area("Caption (you can include #hashtags directly here)")
    
    st.markdown("**📍 Location details**")
    street_num = st.text_input("Street Number *", placeholder="e.g. 123")
    locality = st.text_input("Area/Locality *", placeholder="e.g. Indiranagar")
    city = st.text_input("City *", placeholder="e.g. Bengaluru")
    state = st.text_input("State *", placeholder="e.g. Karnataka")
    
    hashtags = st.text_input("Hashtags * (comma-separated, without #)", placeholder="e.g. food, clothes, education")
    tagged_users = st.text_input("Tag users (comma-separated user IDs, optional)")
    submitted = st.form_submit_button("Share Post", use_container_width=True, disabled=image is None)

if submitted:
    try:
        if not street_num.strip() or not locality.strip() or not city.strip() or not state.strip():
            raise ValueError("All location fields (Street Number, Area/Locality, City, State) are mandatory.")
        if not image:
            raise ValueError("Photo is mandatory.")
        
        combined_location = f"{street_num.strip()}, {locality.strip()}, {city.strip()}, {state.strip()}"
        image_path = save_upload(image, "post_images")
        tag_list = [t.strip() for t in hashtags.split(",")] if hashtags else []
        mention_list = [u.strip() for u in tagged_users.split(",")] if tagged_users else []
        post_id = posts_backend.create_post(
            user["user_id"], caption, image_path, combined_location,
            tag_list, donation_type=None, tagged_users=mention_list,
        )
        
        all_tags = [t.lower() for t in tag_list] + [t.lower() for t in posts_backend.extract_hashtags(caption)]
        if "food" in all_tags:
            st.session_state.post_success_msg = "Post created! 🍲 Note: Your #food donation post will automatically be deleted after 24 hours."
        else:
            st.session_state.post_success_msg = "Post created!"
            
        st.session_state.upload_key += 1
        st.rerun()
    except ValueError as e:
        st.error(str(e))
