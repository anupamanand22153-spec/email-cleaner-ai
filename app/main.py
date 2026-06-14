import os
import sys
import re
import urllib.parse
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests as req_lib
import streamlit as st
from google.oauth2.credentials import Credentials

from app.auth.google_auth import get_google_auth_flow

try:
    from app.database.user_repository import save_user
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    save_user = None

st.set_page_config(page_title="Email Cleaner AI", layout="wide")

# =================================================
# Session State Initialization
# =================================================
for key, default in [
    ("authenticated", False),
    ("credentials", None),
    ("token_fetched", False),
    ("user_saved", True),
    ("user_name", ""),
    ("user_email", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# =================================================
# OAuth Callback Handler
# =================================================
query_params = st.query_params

if (
    "code" in query_params
    and not st.session_state.authenticated
    and not st.session_state.token_fetched
):
    st.session_state.token_fetched = True
    try:
        token_resp = req_lib.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": query_params["code"],
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "redirect_uri": st.secrets["google"]["redirect_uri"],
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        if "error" in token_data:
            raise ValueError(f"Google token error: {token_data}")

        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["google"]["client_id"],
            client_secret=st.secrets["google"]["client_secret"],
            scopes=token_data.get("scope", "").split(),
        )

        userinfo = req_lib.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        ).json()

        st.session_state.credentials = credentials
        st.session_state.user_email = userinfo.get("email", "")
        st.session_state.user_name = userinfo.get("name", "")
        st.session_state.authenticated = True
        st.session_state.user_saved = False
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.session_state.token_fetched = False
        st.error(f"Authentication failed: {e}")
        st.stop()

# =================================================
# Save user to DB on first login
# =================================================
if DB_AVAILABLE and not st.session_state.user_saved and st.session_state.authenticated:
    try:
        save_user(
            email=st.session_state.user_email,
            full_name=st.session_state.user_name,
            provider="google",
        )
        st.session_state.user_saved = True
    except Exception:
        pass

# =================================================
# Sign-in page (unauthenticated)
# =================================================
if not st.session_state.authenticated:
    st.title("📧 Email Cleaner AI")
    st.info("🔒 **READ-ONLY MODE**: This app does NOT delete, move, or modify any emails.")
    st.markdown("""
This AI agent helps you:
- Understand your inbox
- Identify **Important**, **Promotional**, and **Spam** emails
- Reduce inbox overload safely
""")
    st.warning("Please sign in with Google to continue")
    flow = get_google_auth_flow()
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
    )
    st.markdown(f"👉 **[Sign in with Google]({auth_url})**")
    st.stop()

# =================================================
# Authenticated — redirect hint
# =================================================
st.title("📧 Email Cleaner AI")
st.success(f"✅ Logged in as **{st.session_state.user_name}** ({st.session_state.user_email})")
st.info("👈 Use the sidebar to navigate to **Dashboard**, **Inbox**, **Unsubscribe**, or **Settings**.")
