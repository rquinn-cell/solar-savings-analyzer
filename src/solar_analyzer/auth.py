from statistics import mode

import streamlit as st
from src.solar_analyzer.database import get_supabase_client

def render_login_gate():
    """
    Renders a clean Supabase Sign-In / Sign-Up form interface.
    Returns the user's authentic metadata UUID if logged in, otherwise None.
    """
    # Initialize basic session states if missing
    if "user_authenticated" not in st.session_state:
        st.session_state.user_authenticated = False
    if "user_uuid" not in st.session_state:
        st.session_state.user_uuid = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # If already logged in, return early
    if st.session_state.user_authenticated:
        return st.session_state.user_uuid

    st.title("☀️ Solar ROI Analyzer")
    st.caption("Secure multi-tenant platform for Xcel Energy infrastructure management.")

    # 3-Way Mode selector
    mode = st.radio(
        "Account Options", 
        ["Sign In", "Create Account", "Use Anonymously"], 
        horizontal=True, 
        label_visibility="collapsed"
    )

    if mode == "Use Anonymously":
        st.markdown("""
        ### 🔒 Stateless Privacy Mode
        - No email or password required.
        - Your uploaded PDFs are parsed entirely in local system RAM.
        - No data or metadata will ever leave your browser or be saved to the cloud.
        """)
        if st.button("Enter Sandbox Dashboard", use_container_width=True):
            st.session_state.user_authenticated = True
            st.session_state.user_uuid = "ANONYMOUS"
            st.session_state.user_email = "Anonymous Sandbox"
            st.rerun()
        return None

    email = st.text_input("Email Address").strip()
    password = st.text_input("Password", type="password")

    supabase = get_supabase_client()

    if mode == "Sign In":
        if st.button("Log In", use_container_width=True):
            try:
                # Attempt credential handshake with Supabase Auth servers
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                
                st.session_state.user_authenticated = True
                st.session_state.user_uuid = res.user.id
                st.session_state.user_email = res.user.email
                st.toast("Welcome back! Loading security context...")
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")

    elif mode == "Create Account":
        st.info("Passwords must contain at least 6 characters.")
        if st.button("Register & Initialize Storage", use_container_width=True):
            if len(password) < 6:
                st.error("Password is too short.")
                return None
            try:
                # Sign up the user in Supabase Auth
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account initialized successfully! Please sign in using your credentials.")
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")

    return None

def logout_user():
    """Flushes active session states and disconnects the token link."""
    supabase = get_supabase_client()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    # 1. Clear out ALL keys from session state to prevent cross-account cache leakage
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    # 2. Re-initialize baseline authenticated variables to prevent crash loops
    st.session_state.user_authenticated = False
    st.session_state.user_uuid = None
    st.session_state.user_email = None
    st.rerun()