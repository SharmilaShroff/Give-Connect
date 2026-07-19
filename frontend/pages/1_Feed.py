import frontend.utils.bootstrap  # noqa: F401
import streamlit as st

from backend import posts as posts_backend
from backend import profile as profile_backend
from backend.feed import build_feed
from backend import search as search_backend
from frontend.utils.session import require_login
from frontend.utils.badge import name_with_badge
from backend import community as community_backend

st.set_page_config(page_title="GiveConnect", page_icon=":material/favorite:", layout="wide")
user = require_login()



from frontend.utils.navigation import render_sidebar, render_chatbot, render_circular_avatar
render_sidebar()
render_chatbot()



@st.dialog("Report Spam")
def show_spam_dialog(post_id, user_id):
    reason = st.selectbox("Reason", ["Looks like spam", "Scam or fraud", "Other"])
    details = st.text_area("Additional Details (Optional)")
    st.markdown('<div class="insta-primary-btn">', unsafe_allow_html=True)
    if st.button("Submit Report"):
        posts_backend.report_post(user_id, post_id, "spam", details)
        posts_backend.mark_not_interested(user_id, post_id, "spam")
        st.toast("Reported as spam and removed from feed.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Not Interested")
def show_not_interested_dialog(post_id, user_id, poster_id, hashtags):
    st.write("Why are you not interested?")
    options = ["This user"]
    if hashtags: options.append("Posts with these hashtags")
    if hashtags: options.append("Both")
    
    choice = st.radio("Selection", options, label_visibility="collapsed")
    st.markdown('<div class="insta-primary-btn">', unsafe_allow_html=True)
    if st.button("Submit"):
        if choice in ["This user", "Both"]:
            posts_backend.hide_user(user_id, poster_id)
        if choice in ["Posts with these hashtags", "Both"]:
            for t in hashtags:
                posts_backend.hide_hashtag(user_id, t)
        posts_backend.mark_not_interested(user_id, post_id, f"Not interested: {choice}")
        st.toast("Post removed and preferences updated.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Post", width="large")
def show_comments_dialog(post, user_id):
    # This replicates the Instagram modal
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
                st.image(post["image_path"], use_column_width=True)
        else:
            st.write(post.get("caption") or "")
    
    with cols[1]:
        poster = profile_backend.get_user(post["user_id"])
        
        st.markdown(name_with_badge(f"**{poster['full_name']}**", poster["is_verified"]), unsafe_allow_html=True)
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
        comments = posts_backend.get_comments(post["post_id"])
        if comments:
            for c in comments:
                st.markdown(f"**{c['full_name']}** {c['content']}")
        else:
            st.caption("No comments yet.")
            
        st.divider()
        
        action_cols = st.columns([1, 1, 1, 5])
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
            
        if action_cols[1].button(":material/chat_bubble_outline:", key=f"dlg_chat_{post['post_id']}"):
            pass # already in chat view
            
        if action_cols[2].button(":material/send:", key=f"dlg_share_{post['post_id']}"):
            posts_backend.share_post(user_id, post["post_id"])
            st.toast("Shared!")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.write(f"**{posts_backend.get_like_count(post['post_id'])} likes**")

        with st.form(f"comment_form_{post['post_id']}"):
            new_comment = st.text_input("Add a comment...", label_visibility="collapsed", placeholder="Add a comment...")
            if st.form_submit_button("Post"):
                if new_comment.strip():
                    posts_backend.add_comment(user_id, post["post_id"], new_comment.strip())
                    st.rerun()

def render_post_card(post, user):
    posts_backend.register_impression(post["post_id"], user["user_id"])
    
    poster = profile_backend.get_user(post["user_id"])
    poster_img = poster.get("profile_picture") if poster else None

    with st.container(border=True):
        st.markdown('<span class="post-card-marker" style="display:none;"></span>', unsafe_allow_html=True)
        
        # Build avatar base64 directly or use default emoji fallback
        import os, base64
        avatar_html = ""
        if poster_img and os.path.exists(poster_img):
            try:
                with open(poster_img, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                mime = "image/png" if poster_img.endswith(".png") else "image/jpeg"
                avatar_html = f'<img src="data:{mime};base64,{encoded}" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover; border: 1px solid #262626; flex-shrink: 0;">'
            except Exception:
                pass
                
        if not avatar_html:
            avatar_html = '<div style="display: flex; justify-content: center; align-items: center; width: 38px; height: 38px; border-radius: 50%; background-color: #262626; border: 1px solid #333; flex-shrink: 0;"><span style="font-size: 19px;">👤</span></div>'

        header_cols = st.columns([10.5, 1, 0.5], vertical_alignment="center")
        
        display_name_html = name_with_badge(post['user_id'], post["is_verified"])
        header_html = f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-top: -4px; margin-bottom: 8px;">
            {avatar_html}
            <div style="font-size: 17px; font-weight: 600; color: white; display: flex; align-items: center;">
                {display_name_html} 
                <span style="font-size: 14px; font-weight: 400; color: #A8A8A8; margin-left: 6px;">• 1d</span>
            </div>
        </div>
        """
        
        header_cols[0].markdown(header_html, unsafe_allow_html=True)
        
        with header_cols[1].popover(":material/more_horiz:"):
            if st.button("Spam", key=f"spam_btn_{post['post_id']}", use_container_width=True):
                show_spam_dialog(post["post_id"], user["user_id"])
            if st.button("Not interested", key=f"ni_btn_{post['post_id']}", use_container_width=True):
                show_not_interested_dialog(post["post_id"], user["user_id"], post["user_id"], post.get("hashtags") or [])

        if post.get("image_path"):
            import os
            if os.path.exists(post["image_path"]):
                st.image(post["image_path"], use_column_width=True)
        
        st.markdown(
            """
            <style>
            /* Remove border/bg from popover button to match tertiary */
            div[data-testid="stPopover"] > button {
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
            div[data-testid="stPopover"] > button:hover {
                background-color: rgba(255, 255, 255, 0.1) !important;
            }
            </style>
            """, unsafe_allow_html=True
        )
        action_cols = st.columns([1, 1, 1, 7, 1])
        liked = posts_backend.user_liked(post["post_id"], user["user_id"])
        like_icon = ":material/favorite:" if liked else ":material/favorite_border:"
        
        with action_cols[0]:
            if liked:
                st.markdown('<span class="liked-heart-marker" style="display:none;"></span>', unsafe_allow_html=True)
            if st.button(like_icon, key=f"like_{post['post_id']}"):
                if liked:
                    posts_backend.unlike_post(user["user_id"], post["post_id"])
                else:
                    posts_backend.like_post(user["user_id"], post["post_id"])
                st.rerun()
            
        with action_cols[1]:
            if st.button(":material/chat_bubble_outline:", key=f"comment_btn_{post['post_id']}"):
                st.session_state.view_post_id = post["post_id"]
                st.rerun()
            
        with action_cols[2]:
            if st.button(":material/send:", key=f"share_{post['post_id']}"):
                posts_backend.share_post(user["user_id"], post["post_id"])
                st.toast("Shared!")
            
        is_saved = posts_backend.is_saved(user["user_id"], post["post_id"])
        save_icon = ":material/bookmark:" if is_saved else ":material/bookmark_border:"
        with action_cols[4]:
            if is_saved:
                st.markdown('<span class="saved-bookmark-marker" style="display:none;"></span>', unsafe_allow_html=True)
            if st.button(save_icon, key=f"save_{post['post_id']}"):
                if is_saved:
                    posts_backend.unsave_post(user["user_id"], post["post_id"])
                else:
                    posts_backend.save_post(user["user_id"], post["post_id"])
                st.rerun()

        likes_count = posts_backend.get_like_count(post['post_id'])
        if likes_count > 0:
            st.write(f"**{likes_count} likes**")
            
        caption = post.get('caption') or ''
        hashtags = post.get('hashtags')
        if hashtags is None:
            hashtags = posts_backend.get_post_hashtags(post['post_id'])
            
        if hashtags:
            hashtag_str = " ".join([f"#{t}" for t in hashtags])
            st.markdown(f"{caption} <span style='color:#0095F6;'>{hashtag_str}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"{caption}")

if "view_post_id" in st.session_state and st.session_state.view_post_id:
    pid = st.session_state.view_post_id
    st.session_state.view_post_id = None
    post_obj = posts_backend.get_post(pid)
    if post_obj:
        show_comments_dialog(post_obj, user["user_id"])

# Layout: Feed (centered, ~45%), Spacing, Suggestions (right side, ~40%)
# Streamlit columns are relative, so we use spacing columns to center it
col_spacer1, col_feed, col_spacer2, col_suggestions, col_spacer3 = st.columns([0.5, 4.5, 0.5, 4, 0.5])

with col_suggestions:
    st.markdown("<br><br>", unsafe_allow_html=True)
    my_profile = profile_backend.get_user(user["user_id"])
    prof_cols = st.columns([1, 4])
    with prof_cols[0]:
        render_circular_avatar(my_profile.get("profile_picture") if my_profile else None, size=44)
    prof_cols[1].markdown(f"**{user['user_id']}**<br><span style='color:gray; font-size:14px'>{my_profile.get('full_name', '') if my_profile else ''}</span>", unsafe_allow_html=True)
    
    st.write("")
    st.markdown('<span style="color:#A8A8A8; font-weight:600; font-size:14px;">Suggested for you</span>', unsafe_allow_html=True)
    
    with st.container(height=800, border=False):
        all_users = profile_backend.search_users("")
        count = 0
        for r in all_users:
            if r["user_id"] != user["user_id"] and not profile_backend.is_following(user["user_id"], r["user_id"]):
                with st.container(border=True):
                    # Card layout: [Avatar(15%), Text(45%), View(20%), Follow(20%)]
                    s_cols = st.columns([1.5, 4.5, 2, 2])
                    with s_cols[0]:
                        render_circular_avatar(r.get("profile_picture"), size=44)
                    with s_cols[1]:
                        raw_name = r.get("full_name") or r["user_id"]
                        display_name = name_with_badge(raw_name, r.get("is_verified", False))
                        st.markdown(f"<div style='margin-top: 4px; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'><strong>{display_name}</strong><br><span style='font-size: 12px; color: #A8A8A8;'>@{r['user_id']}</span></div>", unsafe_allow_html=True)
                    with s_cols[2]:
                        if st.button("View", key=f"view_sug_{r['user_id']}", use_container_width=True, type="primary"):
                            st.session_state.profile_history = ["__FEED__"]
                            st.session_state.viewing_profile = r["user_id"]
                            st.switch_page("pages/2_Profile.py")
                    with s_cols[3]:
                        if st.button("Follow", key=f"follow_sug_{r['user_id']}", use_container_width=True, type="primary"):
                            profile_backend.follow(user["user_id"], r["user_id"])
                            st.rerun()
                count += 1
                if count >= 15: break
            
with col_feed:
    st.markdown("<br>", unsafe_allow_html=True)
    global_search = st.text_input("🔍 Search GiveConnect...", key="global_search_feed", placeholder="Search users, locations, or hashtags...")
    
    if global_search:
        st.write("")
        t_users, t_locations, t_hashtags = st.tabs(["Users", "Locations", "Hashtags"])
        with t_users:
            res_users = profile_backend.search_users(global_search)
            if not res_users:
                st.write("No users found.")
            else:
                for r in res_users:
                    c1, c2, c3 = st.columns([1, 5, 2])
                    with c1: render_circular_avatar(r.get("profile_picture"), size=40)
                    c2.markdown(name_with_badge(f"**{r['user_id']}**<br><span style='color:gray;'>{r['full_name']}</span>", r["is_verified"]), unsafe_allow_html=True)
                    if c3.button("View Profile", key=f"search_u_{r['user_id']}", use_container_width=True):
                        st.session_state.profile_history = ["__FEED__"]
                        st.session_state.viewing_profile = r["user_id"]
                        st.switch_page("pages/2_Profile.py")
        with t_locations:
            res_locs = search_backend.search_locations(global_search)
            if not res_locs:
                st.write("No locations found.")
            else:
                for l in res_locs:
                    with st.expander(f"📍 {l['location']}"):
                        loc_posts = search_backend.search_posts_by_location(l['location'])
                        if not loc_posts:
                            st.write("No posts found here.")
                        else:
                            for p in loc_posts:
                                render_post_card(p, user)
        with t_hashtags:
            res_tags = search_backend.search_hashtags(global_search)
            if not res_tags:
                st.write("No hashtags found.")
            else:
                for t in res_tags:
                    with st.expander(f"#{t['tag']}"):
                        tag_posts = search_backend.search_posts_by_hashtag(t['tag'])
                        if not tag_posts:
                            st.write("No posts found here.")
                        else:
                            for p in tag_posts:
                                render_post_card(p, user)
        st.stop() # Hide feed if searching

    # ---------------------------------------------------------- BUILD FEED
    override = st.session_state.get("chatbot_search_override")
    
    if override:
        st.markdown(f"#### 🤖 Showing results for: {override['query']}")
        if st.button("Clear Filter"):
            del st.session_state["chatbot_search_override"]
            st.rerun()
            
        ftype = override["filter_type"]
        if ftype == "location":
            feed_posts = search_backend.search_posts_by_location(override["query"])
        elif ftype == "hashtag":
            feed_posts = search_backend.search_posts_by_hashtag(override["query"])
        else:
            # general query
            feed_posts = []
            for t in search_backend.search_hashtags(override["query"]):
                feed_posts.extend(search_backend.search_posts_by_hashtag(t["tag"]))
            for l in search_backend.search_locations(override["query"]):
                feed_posts.extend(search_backend.search_posts_by_location(l["location"]))
                
        # Deduplicate
        seen = set()
        deduped = []
        for p in feed_posts:
            if p["post_id"] not in seen:
                seen.add(p["post_id"])
                deduped.append(p)
        feed_posts = deduped
        
    else:
        interests = (user.get("interests") or "").split(",") if user.get("interests") else []
        feed_posts = build_feed(user["user_id"], interests, limit=25)

    if not feed_posts:
        st.info("No posts to show yet. Follow some users/NGOs or check back soon!")

    for post in feed_posts:
        render_post_card(post, user)
