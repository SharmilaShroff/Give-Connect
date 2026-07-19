import frontend.utils.bootstrap  # noqa: F401
import streamlit as st

from backend import posts as posts_backend
from backend import profile as profile_backend
from backend.file_utils import save_upload
from frontend.utils.session import require_login
from frontend.utils.badge import name_with_badge

st.set_page_config(page_title="Profile - GiveConnect", page_icon=":material/account_circle:", layout="wide")
user = require_login()

from frontend.utils.navigation import render_sidebar, render_chatbot, render_circular_avatar
render_sidebar()
render_chatbot()

viewing_id = st.session_state.get("viewing_profile", user["user_id"])
is_own_profile = viewing_id == user["user_id"]

if "profile_history" not in st.session_state:
    st.session_state.profile_history = []
if not st.session_state.profile_history or st.session_state.profile_history[-1] != viewing_id:
    st.session_state.profile_history.append(viewing_id)

profile_user = profile_backend.get_user(viewing_id)

if not profile_user:
    st.error("User not found.")
    st.stop()

@st.dialog("Followers")
def show_followers_dialog(profile_id, current_user_id):
    followers = profile_backend.get_followers(profile_id)
    if not followers:
        st.write("No followers yet.")
        return
    for f in followers:
        cols = st.columns([1, 3, 2])
        with cols[0]:
            render_circular_avatar(f.get("profile_picture"), size=40)
        with cols[1]:
            st.markdown(name_with_badge(f"**{f['user_id']}**<br><span style='font-size: 14px; color: gray;'>{f['full_name']}</span>", f["is_verified"]), unsafe_allow_html=True)
            if st.button("View Profile", key=f"v_f_{f['user_id']}", use_container_width=True):
                st.session_state.viewing_profile = f["user_id"]
                st.switch_page("pages/2_Profile.py")
        with cols[2]:
            if f["user_id"] != current_user_id:
                if profile_backend.is_following(current_user_id, f["user_id"]):
                    if st.button("Following", key=f"u_f_{f['user_id']}", use_container_width=True):
                        profile_backend.unfollow(current_user_id, f["user_id"])
                        st.rerun()
                else:
                    if st.button("Follow", key=f"f_f_{f['user_id']}", type="primary", use_container_width=True):
                        profile_backend.follow(current_user_id, f["user_id"])
                        st.rerun()
        st.divider()

@st.dialog("Following")
def show_following_dialog(profile_id, current_user_id):
    following = profile_backend.get_following(profile_id)
    if not following:
        st.write("Not following anyone.")
        return
    for f in following:
        cols = st.columns([1, 3, 2])
        with cols[0]:
            render_circular_avatar(f.get("profile_picture"), size=40)
        with cols[1]:
            st.markdown(name_with_badge(f"**{f['user_id']}**<br><span style='font-size: 14px; color: gray;'>{f['full_name']}</span>", f["is_verified"]), unsafe_allow_html=True)
            if st.button("View Profile", key=f"v_fw_{f['user_id']}", use_container_width=True):
                st.session_state.viewing_profile = f["user_id"]
                st.switch_page("pages/2_Profile.py")
        with cols[2]:
            if f["user_id"] != current_user_id:
                if profile_backend.is_following(current_user_id, f["user_id"]):
                    if st.button("Following", key=f"u_fw_{f['user_id']}", use_container_width=True):
                        profile_backend.unfollow(current_user_id, f["user_id"])
                        st.rerun()
                else:
                    if st.button("Follow", key=f"f_fw_{f['user_id']}", type="primary", use_container_width=True):
                        profile_backend.follow(current_user_id, f["user_id"])
                        st.rerun()
        st.divider()

@st.dialog("Post", width="large")
def show_post_dialog(post, user_id):
    st.markdown(
        """
        <span class="post-card-marker" style="display:none;"></span>
        <style>
        div[data-testid="stDialog"] div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
            padding: 0 !important;
        }
        </style>
        """, unsafe_allow_html=True
    )
    cols = st.columns([6, 4], gap="small")
    with cols[0]:
        if post.get("image_path"):
            import os
            if os.path.exists(post["image_path"]):
                st.image(post["image_path"], use_container_width=True)
    
    with cols[1]:
        poster = profile_backend.get_user(post["user_id"])
        st.markdown(name_with_badge(f"**{poster['user_id']}**", poster["is_verified"]), unsafe_allow_html=True)
        st.divider()
        
        caption = post.get('caption') or ''
        hashtags = post.get('hashtags')
        if hashtags is None:
            hashtags = posts_backend.get_post_hashtags(post['post_id'])
            
        if hashtags:
            hashtag_str = " ".join([f"#{t}" for t in hashtags])
            st.markdown(f"{caption} <span style='color:#0095F6;'>{hashtag_str}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"{caption}")
        
        st.write("")
        st.write("**Comments**")
        comments = posts_backend.get_comments(post["post_id"])
        if comments:
            for c in comments:
                st.markdown(f"**{c['user_id']}** {c['content']}")
        else:
            st.caption("No comments yet.")
            
        st.divider()
        
        action_cols = st.columns([1, 1, 1, 4, 1])
        liked = posts_backend.user_liked(post["post_id"], user_id)
        like_icon = ":material/favorite:" if liked else ":material/favorite_border:"
        
        st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
        with action_cols[0]:
            if liked:
                st.markdown('<span class="liked-heart-marker" style="display:none;"></span>', unsafe_allow_html=True)
            if st.button(like_icon, key=f"dlg_like_{post['post_id']}"):
                if liked:
                    posts_backend.unlike_post(user_id, post["post_id"])
                else:
                    posts_backend.like_post(user_id, post["post_id"])
                st.rerun()
                
        with action_cols[1]:
            st.button(":material/chat_bubble_outline:", key=f"dlg_chat_{post['post_id']}")
            
        with action_cols[2]:
            if st.button(":material/send:", key=f"dlg_share_{post['post_id']}"):
                posts_backend.share_post(user_id, post["post_id"])
                st.toast("Shared!")

        is_saved = posts_backend.is_saved(user_id, post["post_id"])
        save_icon = ":material/bookmark:" if is_saved else ":material/bookmark_border:"
        with action_cols[3]:
            if is_saved:
                st.markdown('<span class="saved-bookmark-marker" style="display:none;"></span>', unsafe_allow_html=True)
            if st.button(save_icon, key=f"dlg_save_{post['post_id']}"):
                if is_saved:
                    posts_backend.unsave_post(user_id, post["post_id"])
                else:
                    posts_backend.save_post(user_id, post["post_id"])
                st.rerun()
            
        if is_own_profile:
            with action_cols[4]:
                if st.button(":material/delete:", key=f"dlg_del_{post['post_id']}", help="Delete Post"):
                    posts_backend.delete_post(user_id, post["post_id"])
                    st.success("Post deleted.")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.write(f"**{posts_backend.get_like_count(post['post_id'])} likes**")

        with st.form(f"dlg_comment_form_{post['post_id']}", border=False):
            new_comment = st.text_input("Add a comment...", label_visibility="collapsed", placeholder="Add a comment...")
            if st.form_submit_button("Post"):
                if new_comment.strip():
                    posts_backend.add_comment(user_id, post["post_id"], new_comment.strip())
                    st.rerun()

# Layout constraint (center the profile)
if len(st.session_state.profile_history) > 1:
    if st.button("🔙 Back", key="btn_back"):
        st.session_state.profile_history.pop() # pop current
        prev_page = st.session_state.profile_history[-1]
        if prev_page == "__FEED__":
            st.switch_page("pages/1_Feed.py")
        else:
            st.session_state.viewing_profile = prev_page
            st.rerun()

col_spacer1, col_pic, col_info, col_spacer2 = st.columns([1, 2, 4, 1])

with col_pic:
    st.write("")
    render_circular_avatar(profile_user.get("profile_picture"), size=150)

with col_info:
        header_cols = st.columns([2, 1, 1])
        display_name = name_with_badge(profile_user['user_id'], profile_user.get('is_verified', False))
        header_cols[0].markdown(f"<h3 style='margin-bottom:0;'>{display_name}</h3>", unsafe_allow_html=True)
        
        st.markdown('<div class="insta-secondary-btn">', unsafe_allow_html=True)
        if is_own_profile:
            if header_cols[1].button("Edit profile", use_container_width=True):
                st.session_state.editing_profile = not st.session_state.get("editing_profile", False)
                st.rerun()
        else:
            if profile_backend.is_following(user["user_id"], viewing_id):
                if header_cols[1].button("Following", use_container_width=True):
                    profile_backend.unfollow(user["user_id"], viewing_id)
                    st.rerun()
            else:
                st.markdown('<div class="insta-primary-btn">', unsafe_allow_html=True)
                if header_cols[1].button("Follow", use_container_width=True):
                    profile_backend.follow(user["user_id"], viewing_id)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if header_cols[2].button("Message", use_container_width=True):
                st.session_state.dm_target = viewing_id
                st.switch_page("pages/3_DM.py")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("")
        stat_cols = st.columns([1, 1, 1, 2])
        stat_cols[0].markdown(f"**{len(posts_backend.get_user_posts(viewing_id))}** posts")
        if stat_cols[1].button(f"**{profile_backend.follower_count(viewing_id)}** followers", key="btn_followers"):
            st.session_state.view_followers = viewing_id
            st.rerun()
        if stat_cols[2].button(f"**{profile_backend.following_count(viewing_id)}** following", key="btn_following"):
            st.session_state.view_following = viewing_id
            st.rerun()
        
        st.write("")
        st.markdown(f"**{profile_user.get('full_name', '')}**")
        st.caption(f"{profile_user['account_type'].upper()}")
        if profile_user.get("bio"):
            st.write(profile_user["bio"])

    # ---------------------------------------------------------- EDIT PROFILE (own profile only)
_, col_center, _ = st.columns([1, 6, 1])
with col_center:
    if is_own_profile and st.session_state.get("editing_profile"):
        st.divider()
        st.subheader("Edit Profile")
        with st.form("edit_profile", border=False):
            full_name = st.text_input("Name", value=profile_user.get("full_name") or "")
            bio = st.text_area("Bio", value=profile_user.get("bio") or "")
            new_pic = st.file_uploader("Update profile picture (auto-cropped to 1:1)", type=["png", "jpg", "jpeg"])
            
            st.markdown('<div class="insta-primary-btn">', unsafe_allow_html=True)
            cols = st.columns(2)
            with cols[0]:
                if st.form_submit_button("Save changes", use_container_width=True):
                    pic_path = save_upload(new_pic, "profile_pics") if new_pic else None
                    profile_backend.update_profile(
                        user["user_id"], full_name=full_name, bio=bio,
                        profile_picture=pic_path
                    )
                    st.session_state.editing_profile = False
                    st.success("Profile updated.")
                    st.rerun()
            with cols[1]:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.editing_profile = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin-top:40px; margin-bottom:0;'>", unsafe_allow_html=True)

    # ---------------------------------------------------------- TABS (HTML/CSS trick for centered tabs)
    st.markdown(
        """
        <style>
        /* Center the tabs and style them like Instagram */
        [data-testid="stTabs"] {
            display: flex;
            justify-content: center;
        }
        [data-testid="stTabs"] button {
            color: #A8A8A8 !important;
            font-weight: 600 !important;
            letter-spacing: 1px !important;
            border-top: 1px solid transparent !important;
            border-bottom: none !important;
            padding-top: 15px !important;
            margin: 0 20px !important;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #F5F5F5 !important;
            border-top: 1px solid #F5F5F5 !important;
        }
        
        /* Strict Grid images aspect ratio */
        .grid-img {
            width: 100% !important;
            aspect-ratio: 1 / 1 !important;
            object-fit: cover !important;
            border-radius: 4px;
            display: block;
        }
        .grid-item {
            position: relative;
            cursor: pointer;
            margin-bottom: 8px;
        }
        </style>
        """, unsafe_allow_html=True
    )
    
    tab_posts, tab_saved, tab_tagged = st.tabs(["\u2001:material/grid_on: POSTS\u2001", "\u2001:material/bookmark_border: SAVED\u2001", "\u2001:material/account_box: TAGGED\u2001"])

    import base64
    def render_post_grid(posts, tab_name):
        if not posts:
            st.info("No posts to display.")
            return
            
        grid_cols = st.columns(3, gap="small")
        for i, p in enumerate(posts):
            with grid_cols[i % 3]:
                st.markdown('<div class="grid-item">', unsafe_allow_html=True)
                if p.get("image_path"):
                    import os
                    if os.path.exists(p["image_path"]):
                        with open(p["image_path"], "rb") as f:
                            encoded = base64.b64encode(f.read()).decode()
                        st.markdown(f'<img src="data:image/jpeg;base64,{encoded}" class="grid-img" />', unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='grid-img' style='background:#262626; display:flex; align-items:center; justify-content:center; padding:20px; text-align:center;'>{str(p.get('caption'))[:50]}...</div>", unsafe_allow_html=True)
                
                st.markdown('<div class="insta-secondary-btn" style="margin-top:-5px;">', unsafe_allow_html=True)
                if st.button("View", key=f"view_post_{tab_name}_{p['post_id']}", use_container_width=True):
                    st.session_state.view_post_id = p['post_id']
                    st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)

    with tab_posts:
        st.write("")
        user_posts = posts_backend.get_user_posts(viewing_id)
        render_post_grid(user_posts, "posts")

    with tab_saved:
        st.write("")
        if is_own_profile:
            saved_posts = posts_backend.get_saved_posts(viewing_id)
            render_post_grid(saved_posts, "saved")
        else:
            st.info("Saved posts are only visible to you.")

    with tab_tagged:
        st.write("")
        tagged_posts = posts_backend.get_tagged_posts(viewing_id)
        render_post_grid(tagged_posts, "tagged")

if "view_followers" in st.session_state and st.session_state.view_followers:
    vid = st.session_state.view_followers
    st.session_state.view_followers = None
    show_followers_dialog(vid, user["user_id"])

if "view_following" in st.session_state and st.session_state.view_following:
    vid = st.session_state.view_following
    st.session_state.view_following = None
    show_following_dialog(vid, user["user_id"])

if "view_post_id" in st.session_state and st.session_state.view_post_id:
    pid = st.session_state.view_post_id
    st.session_state.view_post_id = None
    post_obj = posts_backend.get_post(pid)
    if post_obj:
        show_post_dialog(post_obj, user["user_id"])
