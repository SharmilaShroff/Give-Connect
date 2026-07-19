import frontend.utils.bootstrap  # noqa: F401
import streamlit as st

from backend import community as community_backend
from frontend.utils.session import require_login
from frontend.utils.badge import name_with_badge

st.set_page_config(page_title="Community - GiveConnect", page_icon=":material/explore:", layout="wide")
user = require_login()

from frontend.utils.navigation import render_sidebar, render_chatbot
render_sidebar()
render_chatbot()

# ---------------------------------------------------------- LAYOUT
_, col_main, _ = st.columns([1, 6, 1])

with col_main:
    st.write("")
    st.markdown("<h2>Explore Communities</h2>", unsafe_allow_html=True)
    open_community = st.session_state.get("open_community")

    if not open_community:
        # Inject Custom CSS for FAB top-right button
        st.markdown(
            """
            <style>
            .create-community-container {
                position: fixed;
                top: 75px;
                right: 40px;
                z-index: 99999;
            }
            .create-community-container div[data-testid="stPopover"] > button {
                background-color: #0095F6 !important;
                color: white !important;
                font-weight: bold !important;
                box-shadow: 0 4px 10px rgba(0,0,0, 0.4) !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 8px 16px !important;
            }
            .create-community-container div[data-testid="stPopover"] > button:hover {
                background-color: #1877F2 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown('<div class="create-community-container">', unsafe_allow_html=True)
        with st.popover(":material/add: New Community"):
            with st.form("create_community_form", border=False):
                name = st.text_input("Community name", placeholder="Name")
                description = st.text_area("Description", placeholder="Description")
                community_type = st.radio("Type", ["challenge", "discussion"])
                if st.form_submit_button("Create", use_container_width=True, type="primary"):
                    if name.strip():
                        cid = community_backend.create_community(name.strip(), description, community_type, user["user_id"])
                        st.session_state.open_community = cid
                        st.rerun()
                    else:
                        st.error("Community name is required.")
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        my_communities = community_backend.get_user_communities(user["user_id"])
        if my_communities:
            st.markdown("#### Your communities")
            for c in my_communities:
                with st.container(border=True):
                    cols = st.columns([5, 1])
                    icon = ":material/emoji_events:" if c["community_type"] == "challenge" else ":material/forum:"
                    cols[0].markdown(f"**{c['name']}** <span style='color:gray;font-size:12px;'>• {c['community_type']}</span>", unsafe_allow_html=True)
                    cols[0].caption(c.get("description") or "")
                    
                    if cols[1].button("Open", key=f"open_{c['community_id']}", use_container_width=True):
                        st.session_state.open_community = c["community_id"]
                        st.rerun()
        else:
            st.info("You haven't joined any communities yet.")

        st.divider()
        st.markdown("#### Discover communities")
        all_communities = community_backend.get_all_communities()
        joined_ids = {c["community_id"] for c in my_communities}
        for c in all_communities:
            if c["community_id"] in joined_ids:
                continue
            with st.container(border=True):
                cols = st.columns([5, 1])
                cols[0].markdown(f"**{c['name']}** <span style='color:gray;font-size:12px;'>• {c['community_type']}</span>", unsafe_allow_html=True)
                
                if cols[1].button("Join", key=f"join_{c['community_id']}", use_container_width=True, type="primary"):
                    community_backend.join_community(c["community_id"], user["user_id"])
                    st.rerun()

    else:
        st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
        if st.button(":material/arrow_back: Back to all communities"):
            st.session_state.open_community = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        community = next((c for c in community_backend.get_all_communities()
                           if c["community_id"] == open_community), None)
        if not community:
            st.error("Community not found.")
            st.stop()

        st.markdown(f"<h2>{community['name']}</h2>", unsafe_allow_html=True)
        st.caption(community.get("description") or "")
        st.divider()

        if community["community_type"] == "challenge":
            st.markdown("#### Live progress")
            board = community_backend.get_progress_board(community["community_id"])
            
            for row in board:
                pct = min(row["current_value"] / row["target_value"], 1.0) if row["target_value"] else 0
                st.markdown(name_with_badge(f"**{row['full_name']}** — {row['goal_label']}", row["is_verified"]),
                            unsafe_allow_html=True)
                st.progress(pct, text=f"{row['current_value']}/{row['target_value']}")

            my_progress = next((r for r in board if r["user_id"] == user["user_id"]), None)
            with st.expander("Update my progress"):
                with st.form("update_progress", border=False):
                    current = st.number_input("Current value", min_value=0,
                                               value=my_progress["current_value"] if my_progress else 0)
                    target = st.number_input("Target value", min_value=1,
                                              value=my_progress["target_value"] if my_progress else 100)
                    label = st.text_input("Goal label", value=my_progress["goal_label"] if my_progress else "")
                    
                    if st.form_submit_button("Update", use_container_width=True, type="primary"):
                        community_backend.update_progress(community["community_id"], user["user_id"],
                                                            int(current), int(target), label)
                        st.rerun()
            st.divider()
            st.markdown("#### Cheer & chat")
        else:
            st.markdown("#### Discussion Board")

        for m in community_backend.get_messages(community["community_id"]):
            with st.container(border=True):
                st.markdown('<span class="post-card-marker" style="display:none;"></span>', unsafe_allow_html=True)
                urgent_tag = " 🚨 **URGENT**" if m.get("is_urgent") else ""
                st.markdown(name_with_badge(f"**{m['full_name']}**{urgent_tag}", m["is_verified"]),
                            unsafe_allow_html=True)
                if m.get("content"):
                    st.write(m["content"])
                if m.get("image_path"):
                    import os
                    if os.path.exists(m["image_path"]):
                        st.image(m["image_path"], width=300)
                
                react_cols = st.columns([1, 1, 6])
                if react_cols[0].button(f"👍 {m['likes']}", key=f"like_msg_{m['message_id']}"):
                    community_backend.react_to_message(m["message_id"], user["user_id"], "like")
                    st.rerun()
                if react_cols[1].button(f"🎉 {m['celebrations']}", key=f"cel_msg_{m['message_id']}"):
                    community_backend.react_to_message(m["message_id"], user["user_id"], "celebrate")
                    st.rerun()

        with st.form("post_message_form", clear_on_submit=True, border=False):
            content = st.text_area("Write something...", label_visibility="collapsed", placeholder="Write something...")
            is_urgent = False
            if community["community_type"] == "discussion":
                is_urgent = st.checkbox("Requires immediate action")
            
            if st.form_submit_button("Post", use_container_width=True, type="primary"):
                if content.strip():
                    community_backend.post_message(community["community_id"], user["user_id"],
                                                     content.strip(), is_urgent=is_urgent)
                    st.rerun()
