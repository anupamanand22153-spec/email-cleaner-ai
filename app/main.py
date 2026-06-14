# =================================================
# Ensure project root is on PYTHONPATH
# =================================================
import os
import sys
import urllib.parse
from collections import Counter

import pandas as pd

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

try:
    from app.database.user_repository import save_user
    DB_AVAILABLE = True
except Exception as import_err:
    DB_AVAILABLE = False
    save_user = None
    _DB_ERROR = str(import_err)

# =================================================
# Page config
# =================================================
st.set_page_config(
    page_title="Email Cleaner AI",
    layout="wide"
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

if "user_saved" not in st.session_state:
    st.session_state.user_saved = True

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

        userinfo_resp = req_lib.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo = userinfo_resp.json()

        st.session_state.credentials = credentials
        st.session_state.user_email = userinfo.get("email", "")
        st.session_state.user_name = userinfo.get("name", "")
        st.session_state.authenticated = True
        st.session_state.user_saved = False
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

st.divider()

# =================================================
# Authentication
# =================================================
if not st.session_state.authenticated:
    st.markdown(
        """
    This AI agent helps you:

    - Understand your inbox
    - Identify **Important**, **Promotional**, and **Other** emails
    - Reduce inbox overload safely
    """
    )
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
# Logged In — Save User to DB
# =================================================
user_name = st.session_state.get("user_name", "")
user_email = st.session_state.get("user_email", "")

if DB_AVAILABLE and not st.session_state.user_saved:
    try:
        save_user(email=user_email, full_name=user_name, provider="google")
        st.session_state.user_saved = True
    except Exception:
        pass  # Silent fail — DB save is non-critical

# =================================================
# Fetch Emails (once, used for both dashboard + list)
# =================================================
with st.spinner("Loading your inbox..."):
    service = get_gmail_service(st.session_state.credentials)
    emails = fetch_email_metadata(service, max_results=100)

if not emails:
    st.warning("No emails found in your inbox.")
    st.stop()

# Classify all emails
classified = [(e, classify_email(e)) for e in emails]

# =================================================
# Dashboard
# =================================================
st.subheader(f"👋 Welcome, {user_name}")
st.caption(f"Signed in as {user_email}")

st.subheader("📊 Inbox Summary")
st.caption(f"Based on your last {len(emails)} emails")

counts = Counter(cat for _, cat in classified)
for cat in ["Important", "Promotions", "Spam", "Other"]:
    counts.setdefault(cat, 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Important", counts["Important"])
col2.metric("🟡 Promotions", counts["Promotions"])
col3.metric("🔴 Spam", counts["Spam"])
col4.metric("⚪ Other", counts["Other"])

chart_df = pd.DataFrame(
    {"Emails": [counts["Important"], counts["Promotions"], counts["Spam"], counts["Other"]]},
    index=["Important", "Promotions", "Spam", "Other"]
)
st.bar_chart(chart_df, color="#4F8BF9")

st.divider()

# =================================================
# Email Filter + List
# =================================================
st.subheader("📂 Filter Emails")

category_filter = st.selectbox(
    "Show emails by category:",
    ["All", "Important", "Promotions", "Spam", "Other"]
)

st.subheader("📨 Recent Emails")

filtered = [(e, cat) for e, cat in classified if category_filter == "All" or cat == category_filter]

if not filtered:
    st.info(f"No emails found in category: {category_filter}")
    st.stop()

for email, category in filtered:
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
