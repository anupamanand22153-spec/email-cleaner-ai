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
import streamlit as st

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
        flow = get_google_auth_flow()

        # Match the state Google returned so requests_oauthlib
        # does not raise MismatchingStateError on fresh sessions
        if "state" in query_params:
            flow.oauth2session._state = query_params["state"]

        redirect_uri = st.secrets["google"]["redirect_uri"]

        # Build the full authorization response URL so that
        # redirect_uri is sent correctly to Google's token endpoint
        auth_response = (
            redirect_uri
            + "?"
            + urllib.parse.urlencode(dict(query_params))
        )

        flow.fetch_token(authorization_response=auth_response)

        st.session_state.credentials = flow.credentials
        st.session_state.authenticated = True
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.session_state.token_fetched = False
        st.error(f"Authentication failed: {type(e).__name__}: {str(e)}")
        st.write("**Redirect URI used:**", st.secrets["google"]["redirect_uri"])
        st.write("**Query params received:**", dict(query_params))
        st.exception(e)
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
