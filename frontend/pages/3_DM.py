import frontend.utils.bootstrap  # noqa: F401
import streamlit as st
import pandas as pd

from backend import dm as dm_backend
from backend import profile as profile_backend
from backend.file_utils import save_upload
from frontend.utils.session import require_login
from frontend.utils.badge import name_with_badge

st.set_page_config(page_title="Messages - GiveConnect", page_icon=":material/chat:", layout="wide")
user = require_login()

from frontend.utils.navigation import render_sidebar, render_chatbot, render_circular_avatar
render_sidebar()
render_chatbot()

# Modern 2-column layout
col_inbox, col_chat = st.columns([3.5, 6.5], gap="large")

with col_inbox:
    st.markdown("<h2 style='margin-bottom:20px;'>Messages</h2>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <style>
        .search-bar div[data-baseweb="input"] {
            border-radius: 20px !important;
            border: 1px solid #202024 !important;
            background-color: #18181B !important;
        }
        </style>
        """, unsafe_allow_html=True
    )
    st.markdown('<div class="search-bar">', unsafe_allow_html=True)
    search = st.text_input("Search users...", label_visibility="collapsed", placeholder="🔍 Search users...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if search:
        for r in profile_backend.search_users(search):
            if r["user_id"] == user["user_id"]:
                continue
            if st.button(f"{r['user_id']}", key=f"newdm_{r['user_id']}", use_container_width=True):
                st.session_state.dm_target = r["user_id"]
                st.rerun()

    target = st.session_state.get("dm_target")
    st.write("")
    
    # CSS for conversation items
    st.markdown(
        """
        <style>
        .convo-card {
            background-color: #0F0F10;
            border: 1px solid #202024;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .convo-card:hover {
            background-color: #18181B;
            border-color: #3F3F46;
        }
        .convo-card.active-card {
            background-color: #18181B;
            border-color: #4F46E5;
            border-left: 4px solid #4F46E5;
            box-shadow: 0 0 10px rgba(79, 70, 229, 0.1);
        }
        /* Hide buttons aggressively using :has() if supported */
        div.element-container:has(.convo-card) + div.element-container {
            display: none !important;
            position: absolute !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        </style>
        """, unsafe_allow_html=True
    )
    
    inbox = dm_backend.get_inbox(user["user_id"])
    
    # Scrollable list
    with st.container(height=650, border=False):
        for convo in inbox:
            other_id = convo["other_user"]
            other = profile_backend.get_user(other_id)
            if not other:
                continue
            
            is_active_class = "active-card" if other_id == target else ""
            
            # Properly load local images via base64 for pure HTML rendering
            import base64, os
            img_path = other.get("profile_picture")
            avatar_html = ""
            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode()
                    mime = "image/png" if img_path.endswith(".png") else "image/jpeg"
                    avatar_html = f'<img src="data:{mime};base64,{encoded}" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; flex-shrink: 0;">'
                except Exception:
                    pass
                    
            if not avatar_html:
                avatar_html = '<div style="display: flex; justify-content: center; align-items: center; width: 48px; height: 48px; border-radius: 50%; background-color: #262626; border: 1px solid #333; flex-shrink: 0;"><span style="font-size: 24px;">👤</span></div>'
            
            last_msg = convo.get("last_content") or ""
            
            # Pure HTML card guarantees exactly one box, no nesting, perfect spacing
            html = f"""
            <div class="convo-card {is_active_class}">
               <div style="display: flex; align-items: center; gap: 16px;">
                   {avatar_html}
                   <div style="flex-grow: 1; overflow: hidden;">
                       <div style="font-weight: bold; color: white; font-size: 16px; margin-bottom: 2px;">{name_with_badge(other_id, other.get("is_verified", False))}</div>
                       <div style="color: #A8A8A8; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{last_msg}</div>
                   </div>
               </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
            
            # Hidden native button for state routing
            if st.button("Open", key=f"inbox_{other_id}"):
                st.session_state.dm_target = other_id
                st.rerun()
                
    # JS Injection to bind HTML card clicks to the native Streamlit buttons
    import streamlit.components.v1 as components
    components.html("""
    <script>
    setInterval(() => {
        try {
            const cards = window.parent.document.querySelectorAll('.convo-card');
            cards.forEach(card => {
                if (!card.dataset.clickBound) {
                    card.dataset.clickBound = 'true';
                    
                    // Fallback to hide button if CSS :has() is not supported
                    const btnContainer = card.closest('.element-container').nextElementSibling;
                    if(btnContainer && btnContainer.querySelector('button')) {
                        btnContainer.style.display = 'none';
                    }
                    
                    card.onclick = function() {
                        if(btnContainer) {
                            const btn = btnContainer.querySelector('button');
                            if(btn) btn.click();
                        }
                    };
                }
            });
        } catch (e) {}
    }, 500);
    </script>
    """, height=0, width=0)

with col_chat:
    if not target:
        st.write("")
        st.markdown("<div style='text-align: center; color: #A8A8A8;'><br><br><br><br><h3>Select a conversation</h3><p>Choose a user from the left to start messaging.</p></div>", unsafe_allow_html=True)
    else:
        other = profile_backend.get_user(target)
        
        # Header for chat
        st.markdown("<div style='padding: 8px 16px; border-bottom: 1px solid #202024; margin-bottom: 16px;'>", unsafe_allow_html=True)
        head_cols = st.columns([1, 8, 3])
        with head_cols[0]:
            render_circular_avatar(other.get("profile_picture"), size=48)
        with head_cols[1]:
            display_name = name_with_badge(other['user_id'], other.get("is_verified", False))
            st.markdown(f"<div style='margin-top: 6px; font-size: 16px;'><strong>{display_name}</strong><br><span style='color:gray; font-size:13px;'>{other['full_name']}</span></div>", unsafe_allow_html=True)
        with head_cols[2]:
            st.write("")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Messages Area
        messages = dm_backend.get_messages(user["user_id"], target)
        chat_box = st.container(height=550, border=False)
        with chat_box:
            if not messages:
                st.markdown("<div style='text-align: center; color: #A8A8A8; margin-top: 50px;'>Start your conversation by sending a message.</div>", unsafe_allow_html=True)
            else:
                for m in messages:
                    is_me = m["sender_id"] == user["user_id"]
                    
                    if is_me:
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-end; margin-bottom: 16px;">
                                <div style="background-color: #4F46E5; color: white; padding: 12px 16px; border-radius: 18px 18px 4px 18px; max-width: 70%; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                                    <div style="font-size: 15px;">{m.get("content", "")}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: flex-start; margin-bottom: 16px;">
                                <div style="background-color: #202024; color: #F5F5F5; padding: 12px 16px; border-radius: 18px 18px 18px 4px; max-width: 70%; position: relative; border: 1px solid #27272A; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                                    <div style="font-size: 15px;">{m.get("content", "")}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True
                        )
                    
                    if m.get("image_path"):
                        import os
                        if os.path.exists(m["image_path"]):
                            if is_me:
                                cc1, cc2 = st.columns([2, 1])
                                with cc2: st.image(m["image_path"], use_container_width=True)
                            else:
                                cc1, cc2 = st.columns([1, 2])
                                with cc1: st.image(m["image_path"], use_container_width=True)

        # Chat Input CSS
        st.markdown(
            """
            <style>
            [data-testid="stChatInput"] {
                padding-bottom: 20px !important;
            }
            [data-testid="stChatInput"] textarea {
                background-color: #18181B !important;
                color: #F5F5F5 !important;
            }
            [data-testid="stChatInput"] button {
                background-color: #4F46E5 !important;
                color: white !important;
            }
            [data-testid="stChatInput"] svg {
                fill: white !important;
            }
            </style>
            """, unsafe_allow_html=True
        )
        
        prompt = st.chat_input("Type a message...")
        if prompt:
            dm_backend.send_message(user["user_id"], target, prompt.strip(), None)
            st.rerun()
