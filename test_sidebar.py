import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
/* CSS for hover to expand sidebar */
[data-testid="stSidebar"] {
    width: 70px !important;
    min-width: 70px !important;
    max-width: 70px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    overflow-x: hidden !important;
    padding-left: 0px !important;
    padding-right: 0px !important;
}

[data-testid="stSidebar"]:hover {
    width: 250px !important;
    min-width: 250px !important;
    max-width: 250px !important;
}

/* Hide Streamlit's default sidebar collapse/expand button */
[data-testid="collapsedControl"] {
    display: none !important;
}

/* Ensure text doesn't wrap */
[data-testid="stSidebar"] * {
    white-space: nowrap !important;
}

/* Adjust page links padding */
[data-testid="stSidebar"] a {
    padding-left: 15px !important;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.page_link("test_sidebar.py", label="Home", icon="🏠")
st.sidebar.page_link("test_sidebar.py", label="Messages", icon="💬")
st.sidebar.page_link("test_sidebar.py", label="Create Post", icon="➕")
st.sidebar.page_link("test_sidebar.py", label="Community", icon="👥")

st.title("Main Content")
