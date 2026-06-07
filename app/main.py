# =================================================
# Ensure project root is on PYTHONPATH
# =================================================
import os
import sys
import urllib.parse

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =================================================
# Imports
# =================================================
import requests as req_lib
import streamlit as st
from google.oauth2.credentials import Credentials

from app.auth.google_auth import get_google_auth_flow
from app.gmail2.gmail_service import (
    get_gmail_service,
    fetch_email_metadata
)
from app.logic.email_classifier import classify_email

# =================================================
# Page config
# =================================================
st.set_page_config(
    page_title="Email Cleaner AI",
    layout="centered"
)

# =================================================
# Session State Initialization
# =================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "credentials" not in st.session_state:
    st.session_state.credentials = None

if "token_fetched" not in st.session_state:
    st.session_state.token_fetched = False

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
        # Call Google's token endpoint directly to avoid any
        # library-level encoding or redirect_uri issues
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

        st.session_state.credentials = credentials
        st.session_state.authenticated = True
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.session_state.token_fetched = False
        st.error(f"Authentication failed: {type(e).__name__}: {str(e)}")
        st.stop()

# =================================================
# UI Header
# =================================================
st.title("📧 Email Cleaner AI")

st.info(
    "🔒 **READ-ONLY MODE**: This app does NOT delete, move, or modify any emails."
)

st.markdown(
    """
This AI agent helps you:

- Understand your inbox
- Identify **Important**, **Promotional**, and **Other** emails
- Reduce inbox overload safely
"""
)

st.divider()

# =================================================
# Authentication
# =================================================
if not st.session_state.authenticated:
    st.warning("Please sign in with Google to continue")

    flow = get_google_auth_flow()
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )

    st.markdown(f"👉 **[Sign in with Google]({auth_url})**")
    st.stop()

# =================================================
# Logged In State
# =================================================
st.success("✅ Logged in successfully")

service = get_gmail_service(st.session_state.credentials)
emails = fetch_email_metadata(service, max_results=20)

# =================================================
# Email Filter
# =================================================
st.subheader("📂 Filter Emails")

category_filter = st.selectbox(
    "Show emails by category:",
    ["All", "Important", "Promotions", "Spam", "Other"]
)

# =================================================
# Email Display
# =================================================
st.subheader("📨 Recent Emails")

if not emails:
    st.warning("No emails found.")
    st.stop()

for email in emails:
    category = classify_email(email)

    if category_filter != "All" and category != category_filter:
        continue

    badge = {
        "Important": "🟢 IMPORTANT",
        "Promotions": "🟡 PROMOTION",
        "Spam": "🔴 SPAM",
        "Other": "⚪ OTHER"
    }.get(category, "⚪ OTHER")

    with st.container():
        st.markdown(f"**From:** {email.get('From', 'N/A')}")
        st.markdown(f"**Subject:** {email.get('Subject', 'N/A')}")
        st.markdown(f"**Date:** {email.get('Date', 'N/A')}")
        st.markdown(f"**Category:** {badge}")
        st.divider()
