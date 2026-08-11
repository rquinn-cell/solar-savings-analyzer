import streamlit as st
from src.solar_analyzer.database import get_supabase_client

DEMO_USER_UUID = "f98b28b9-7a38-4342-8494-3ca5976cefb4"

def render_login_gate():
    """
    Renders a clean Supabase Sign-In / Sign-Up / Demo form interface.
    Returns the user's authentic metadata UUID if logged in, DEMO_USER_UUID for Demo Mode, 
    or None if unauthenticated.
    """
    # Initialize basic session states if missing
    if "user_authenticated" not in st.session_state:
        st.session_state.user_authenticated = False
    if "user_uuid" not in st.session_state:
        st.session_state.user_uuid = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "is_demo" not in st.session_state:
        st.session_state.is_demo = False

    # If already authenticated or active in Demo Mode, return active UUID early
    if st.session_state.user_authenticated:
        return st.session_state.user_uuid

    st.title("☀️ Solar ROI Analyzer")
    st.caption("Secure solar savings analyzer for Colorado residential Xcel customers.")

    # 4-Way Mode selector incorporating Interactive Demo Mode
    mode = st.radio(
        "Account Options", 
        ["🚀 Try Interactive Demo", "Sign In", "Create Account", "Use Anonymously"], 
        horizontal=True, 
        label_visibility="collapsed"
    )

    # --- MODE 1: INTERACTIVE DEMO MODE ---
    if mode == "🚀 Try Interactive Demo":
        st.markdown("""
        ### ⚡ Interactive Demo Mode
        - Explore real, pre-loaded Xcel Energy bill summaries and TOU savings charts.
        - **Read-Only Access:** PDF uploading and cloud sync modifications are disabled.
        - Zero registration or login credentials required.
        """)
        if st.button("Launch Interactive Demo", type="primary", use_container_width=True):
            st.session_state.user_authenticated = True
            st.session_state.user_uuid = DEMO_USER_UUID
            st.session_state.user_email = "Demo User (Read-Only)"
            st.session_state.is_demo = True
            st.rerun()
        return None

    # --- MODE 2: STATELESS ANONYMOUS SANDBOX ---
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
            st.session_state.is_demo = False
            st.rerun()
        return None

    # --- MODE 3 & 4: REGISTERED CREDENTIAL HANDSHAKE ---
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
                st.session_state.is_demo = False
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

    # Clear out ALL keys from session state to prevent cross-account cache leakage
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    # Re-initialize baseline authenticated variables
    st.session_state.user_authenticated = False
    st.session_state.user_uuid = None
    st.session_state.user_email = None
    st.session_state.is_demo = False
    st.rerun()