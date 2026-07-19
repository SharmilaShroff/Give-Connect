"""
GiveConnect navigation, sidebar, circular avatar and floating chatbot overlay utility.
"""
import streamlit as st
import os
import base64
from backend.notifications import get_unread_count, get_unread_messages_count, get_recent_notifications, mark_all_read, mark_read
from backend.langgraph_flows.chatbot_flow import run_chatbot_flow
from backend.posts import get_post
from frontend.utils.badge import name_with_badge


def inject_custom_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    theme = st.session_state.theme
    
    if theme == "dark":
        bg_color = "#0F0F10"
        sec_bg = "#18181B"
        card_bg = "#202024"
        border_color = "#27272A"
        text_color = "#F5F5F5"
        sec_text = "#A8A8A8"
        accent = "#4F46E5"
    else:
        bg_color = "#FFFFFF"
        sec_bg = "#FFFFFF"
        card_bg = "#F8F9FA"
        border_color = "#DBDBDB"
        text_color = "#000000"
        sec_text = "#737373"
        accent = "#4F46E5"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }}
        
        /* Streamlit background overrides */
        .stApp {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}
        
        /* Custom Cards for Instagram Look */
        .custom-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            color: {text_color};
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: {sec_bg} !important;
            width: 72px !important;
            min-width: 72px !important;
            max-width: 72px !important;
            transition: width 0.2s ease-in-out !important;
            overflow-x: hidden !important;
            border-right: 1px solid {border_color} !important;
        }}
        
        @media (min-width: 1264px) {{
            [data-testid="stSidebar"] {{
                width: 244px !important;
                min-width: 244px !important;
                max-width: 244px !important;
            }}
        }}
        
        /* Hide default sidebar toggle */
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        
        /* Sidebar Links and Text */
        [data-testid="stSidebar"] * {{
            white-space: nowrap !important;
        }}
        
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        
        /* Adjust page links padding */
        [data-testid="stSidebar"] a {{
            padding-left: 12px !important;
            color: {text_color} !important;
            border-radius: 8px !important;
            margin: 4px 12px !important;
        }}
        
        [data-testid="stSidebar"] a:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}
        
        /* Notifications styling for theme */
        .unread-dot {{
            height: 8px;
            width: 8px;
            background-color: #FF3040;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }}
        .notification-item {{
            padding: 0px !important;
            border-bottom: 1px solid {border_color};
            background-color: {card_bg};
        }}
        .notification-item button {{
            background: transparent !important;
            border: none !important;
            color: {text_color} !important;
            text-align: left !important;
            width: 100% !important;
            padding: 12px 16px !important;
            font-size: 0.9rem !important;
        }}
        .notification-item button:hover {{
            background-color: rgba(255,255,255,0.05) !important;
        }}
        .notification-item.unread button {{
            font-weight: 600 !important;
            background-color: {sec_bg} !important;
        }}
        
        /* Dialog Modal */
        [data-testid="stDialog"] {{
            background-color: {sec_bg} !important;
            border-radius: 8px !important;
            color: {text_color} !important;
            border: 1px solid {border_color};
        }}
        
        /* Remove default button backgrounds if they are icon buttons */
        .icon-btn button {{
            background-color: transparent !important;
            border: none !important;
            color: {text_color} !important;
            box-shadow: none !important;
            padding: 8px !important;
            font-size: 1.2rem !important;
        }}
        /* Icon Buttons inside Post Cards ONLY */
        [data-testid="stVerticalBlockBorderWrapper"]:has(.post-card-marker) button[kind="secondary"],
        [data-testid="stDialog"]:has(.post-card-marker) button[kind="secondary"] {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 8px !important;
            font-size: 1.75rem !important; /* Increased from 1.2rem */
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:has(.post-card-marker) button[kind="secondary"] span,
        [data-testid="stDialog"]:has(.post-card-marker) button[kind="secondary"] span {{
            font-size: 1.75rem !important; /* Ensure material symbol inherits */
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:has(.post-card-marker) button[kind="secondary"]:hover,
        [data-testid="stDialog"]:has(.post-card-marker) button[kind="secondary"]:hover {{
            background-color: transparent !important;
            color: {sec_text} !important;
        }}
        
        /* Modern Outlined Primary Button */
        div[data-testid="stButton"] button[kind="primary"] {{
            background-color: transparent !important;
            color: {text_color} !important;
            border-radius: 8px !important;
            border: 1px solid {accent} !important;
            font-weight: 600 !important;
            padding: 6px 12px !important;
            white-space: nowrap !important;
            transition: all 0.2s ease !important;
        }}
        div[data-testid="stButton"] button[kind="primary"]:hover, 
        div[data-testid="stButton"] button[kind="primary"]:active {{
            background-color: rgba(79, 70, 229, 0.1) !important;
            border-color: {accent} !important;
        }}
        div[data-testid="stButton"] button[kind="primary"] p {{
            white-space: nowrap !important;
        }}
        
        /* Modern Outlined Secondary Button */
        div[data-testid="stButton"] button[kind="secondary"] {{
            background-color: transparent !important;
            color: {text_color} !important;
            border-radius: 8px !important;
            border: 1px solid {border_color} !important;
            font-weight: 600 !important;
            padding: 6px 12px !important;
            white-space: nowrap !important;
            transition: all 0.2s ease !important;
        }}
        div[data-testid="stButton"] button[kind="secondary"]:hover, 
        div[data-testid="stButton"] button[kind="secondary"]:active {{
            background-color: {sec_bg} !important;
            border-color: #3f3f46 !important;
        }}
        div[data-testid="stButton"] button[kind="secondary"] p {{
            white-space: nowrap !important;
        }}
        
        /* Hide element borders for clean look */
        div[data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
        }}
        
        /* General Dividers */
        hr {{
            border-color: {border_color} !important;
            margin: 1em 0 !important;
        }}
        
        @keyframes icon-pop {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.15); }}
            100% {{ transform: scale(1); }}
        }}
        
        /* Hide the marker containers so they don't break flex spacing */
        div.element-container:has(.saved-bookmark-marker),
        div.element-container:has(.liked-heart-marker),
        div.element-container:has(.home-marker) {{
            display: none !important;
            position: absolute !important;
        }}
        
        /* Apply styles and animations when markers are present */
        div.element-container:has(.saved-bookmark-marker) + div.element-container button {{
            color: #4F46E5 !important;
            animation: icon-pop 250ms ease-out;
        }}
        
        div.element-container:has(.liked-heart-marker) + div.element-container button {{
            color: #FF3040 !important;
            animation: icon-pop 250ms ease-out;
        }}
        
        </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    inject_custom_theme()

    user = st.session_state.get("user")
    if not user:
        return

    # Real-time Notifications st.toast check
    recent_notifs = get_recent_notifications(user["user_id"], limit=50)
    
    if "last_seen_notification_id" not in st.session_state:
        st.session_state.last_seen_notification_id = 0
        if recent_notifs:
            st.session_state.last_seen_notification_id = max(n["notification_id"] for n in recent_notifs)

    # Toast new notifications
    if recent_notifs:
        new_notifs = [n for n in recent_notifs if n["notification_id"] > st.session_state.last_seen_notification_id]
        for notif in new_notifs:
            st.toast(f"🔔 {notif['content']}", icon="📢")
        st.session_state.last_seen_notification_id = max(n["notification_id"] for n in recent_notifs)

    # Render Custom Sidebar
    st.sidebar.markdown(
        """
        <div style="font-family: 'Brush Script MT', cursive; font-size: 24px; padding: 20px 12px; margin-bottom: 20px;">
        GiveConnect
        </div>
        """, unsafe_allow_html=True
    )
    
    unread_c = get_unread_count(user["user_id"])
    
    unread_msgs = get_unread_messages_count(user["user_id"])
    dm_label = f"Messages 🔵 {unread_msgs}" if unread_msgs > 0 else "Messages"
    
    if user["account_type"] == "admin":
        st.sidebar.page_link("pages/7_Admin_Dashboard.py", label="Dashboard", icon=":material/dashboard:")
        st.sidebar.page_link("pages/8_Admin_Reports.py", label="Reported Posts", icon=":material/report:")
        st.sidebar.page_link("pages/9_Admin_Users.py", label="User Moderation", icon=":material/group:")
        st.sidebar.page_link("pages/10_Admin_Verification.py", label="NGO Verification", icon=":material/verified:")
    else:
        st.sidebar.page_link("pages/1_Feed.py", label="Home", icon=":material/home:")
                
        st.sidebar.page_link("pages/3_DM.py", label=dm_label, icon=":material/chat:")
        st.sidebar.page_link("pages/5_Create_Post.py", label="Create", icon=":material/add_box:")
        st.sidebar.page_link("pages/4_Community.py", label="Explore", icon=":material/explore:")
        st.sidebar.page_link("pages/6_MyProfile.py", label="Profile", icon=":material/account_circle:")
        
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    
    # Notifications section in a popover to mimic Instagram's heart icon panel
    if user["account_type"] != "admin":
        notif_label = f":material/favorite: Notifications ({unread_c})" if unread_c > 0 else ":material/favorite: Notifications"
        with st.sidebar.popover(notif_label):
            st.markdown("#### Notifications")
            
            unread_notifs = [n for n in recent_notifs if not n["is_read"]]
            
            if unread_notifs:
                for n in unread_notifs:
                    unread_class = "unread"
                    dot = "🔴 "
                    
                    st.markdown(f'<div class="notification-item {unread_class}">', unsafe_allow_html=True)
                    if st.button(f"{dot}{n['content']}", key=f"notif_btn_{n['notification_id']}", use_container_width=True):
                        mark_read(n['notification_id'])
                        if n["notification_type"] in ["comment_tag", "like", "post_tag", "comment"]:
                            st.session_state.view_post_id = n["reference_id"]
                            st.switch_page("pages/1_Feed.py")
                        elif n["notification_type"] == "new_message":
                            st.session_state.dm_target = n["sender_id"]
                            st.switch_page("pages/3_DM.py")
                        elif n["notification_type"] == "follow":
                            st.session_state.viewing_profile = n["sender_id"]
                            st.switch_page("pages/2_Profile.py")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                st.divider()
                st.markdown('<div class="insta-primary-btn">', unsafe_allow_html=True)
                if st.button("Mark as Read", key="mark_all_read_btn", use_container_width=True):
                    mark_all_read(user["user_id"])
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption("No new notifications.")

    # More / Settings Menu at bottom
    with st.sidebar.popover(":material/menu: More"):
        display_name = name_with_badge(f"@{user['user_id']}", user.get('is_verified', False))
        st.markdown(f"**{display_name}**", unsafe_allow_html=True)
        st.divider()
        if st.button("Log out", key="logout_btn", use_container_width=True):
            st.session_state.user = None
            st.switch_page("Home.py")


def render_chatbot():
    # Robust CSS targeting via adjacent sibling combinator instead of :has() to prevent FOUC
    st.markdown(
        """
        <style>
        /* Floating Chatbot FAB container */
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] {
            position: fixed !important;
            bottom: 30px !important;
            right: 30px !important;
            z-index: 100000 !important;
            width: auto !important;
        }
        
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] > button {
            border-radius: 50% !important;
            width: 64px !important;
            height: 64px !important;
            background: linear-gradient(135deg, #4F46E5, #3730A3) !important;
            color: transparent !important;
            box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
        }
        
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] > button:hover {
            transform: scale(1.1) !important;
            box-shadow: 0 8px 25px rgba(79, 70, 229, 0.6) !important;
        }
        
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] > button svg {
            display: none !important; /* Hide chevron */
        }
        
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] > button p {
            display: none !important; /* Hide standard text */
        }
        
        div.element-container:has(span.chatbot-marker) + div.element-container div[data-testid="stPopover"] > button::after {
            content: "🤖";
            font-size: 42px !important;
            position: absolute !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<span class="chatbot-marker" style="display:none;"></span>', unsafe_allow_html=True)
    with st.popover("🤖", help="Chat with AI Donation Assistant"):
        st.markdown("### 🤖 Donation Assistant")
        st.caption("Tell me what you'd like to donate and where.")
        
        chat_box = st.container(height=300, border=True)
        with chat_box:
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            if not st.session_state.chat_history:
                st.markdown("👋 Hello! Ask me e.g. *'I want to donate food near Bengaluru'* or *'Looking for NGO accepting clothes'*.")
            for turn in st.session_state.chat_history:
                with st.chat_message(turn["role"]):
                    st.write(turn["content"])

        with st.form("chatbot_chat_form", clear_on_submit=True):
            cols = st.columns([4, 1])
            user_msg = cols[0].text_input("Message", label_visibility="collapsed", placeholder="Ask something...")
            send_btn = cols[1].form_submit_button("Send")

        if send_btn and user_msg.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_msg.strip()})
            
            with chat_box:
                with st.chat_message("user"):
                    st.write(user_msg.strip())

            try:
                result = run_chatbot_flow(user_msg.strip(), st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "assistant", "content": result["reply"]})
                
                with chat_box:
                    with st.chat_message("assistant"):
                        st.write(result["reply"])
                        for pid in result.get("matched_post_ids", []):
                            post = get_post(pid)
                            if post:
                                with st.container(border=True):
                                    if post.get("image_path") and os.path.exists(post["image_path"]):
                                        st.image(post["image_path"], width=150)
                                    st.write(post.get("caption") or "")
                                    st.caption(f"📍 {post['location']}")
                                    
                nav_action = result.get("navigation_action")
                nav_params = result.get("navigation_params", {})
                
                if nav_action == "profile" and "user_id" in nav_params:
                    st.session_state.profile_history = ["__FEED__"]
                    st.session_state.viewing_profile = nav_params["user_id"]
                    st.switch_page("pages/2_Profile.py")
                elif nav_action == "feed_filter":
                    st.session_state.chatbot_search_override = nav_params
                    st.switch_page("pages/1_Feed.py")
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I ran into an error: {e}"})
            st.rerun()


def render_circular_avatar(image_path, size=140):
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
            st.markdown(
                f'<div style="display: flex; justify-content: center; margin: 10px 0;">'
                f'<img src="data:{mime_type};base64,{encoded}" '
                f'style="border-radius: 50%; object-fit: cover; width: {size}px; height: {size}px; border: 1px solid #262626;" />'
                f'</div>',
                unsafe_allow_html=True
            )
            return True
        except Exception:
            pass
    # Fallback to circular icon
    st.markdown(
        f'<div style="display: flex; justify-content: center; align-items: center; margin: 10px auto;'
        f'border-radius: 50%; width: {size}px; height: {size}px; background-color: #262626; border: 1px solid #333;">'
        f'<span style="font-size: {size//2}px;">👤</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    return False
