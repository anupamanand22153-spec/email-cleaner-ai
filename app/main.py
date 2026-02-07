# =================================================
# Ensure project root is on PYTHONPATH (Windows fix)
# =================================================
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =================================================
# Imports
# =================================================
import streamlit as st

from app.auth.google_auth import get_google_auth_flow
from app.gmail2.gmail_service import get_gmail_service, fetch_email_metadata
from app.logic.email_classifier import classify_email

# =================================================
# Page config (MUST be first Streamlit command)
# =================================================
st.set_page_config(
    page_title="Email Cleaner AI",
    layout="centered"
)

# =================================================
# Session State
# =================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "credentials" not in st.session_state:
    st.session_state.credentials = None

# =================================================
# OAuth callback
# =================================================
query_params = st.query_params

if "code" in query_params and not st.session_state.authenticated:
    flow = get_google_auth_flow()
    flow.fetch_token(code=query_params["code"])

    st.session_state.credentials = flow.credentials
    st.session_state.authenticated = True

    # Clear URL params
    st.query_params.clear()

# =================================================
# UI Header
# =================================================
st.title("📧 Email Cleaner AI")

st.info(
    "🔒 **READ‑ONLY MODE**: This app does NOT delete, move, or modify any emails."
)

st.markdown("""
This AI agent helps you:
- Understand your inbox  
- Identify **Important**, **Promotional**, and **Other** emails  
- Reduce inbox overload safely  
""")

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
# Logged-in state
# =================================================
st.success("✅ Logged in successfully")

service = get_gmail_service(st.session_state.credentials)
emails = fetch_email_metadata(service, max_results=20)

# =================================================
# Category filter
# =================================================
st.subheader("📂 Filter Emails")

category_filter = st.selectbox(
    "Show emails by category:",
    ["All", "Important", "Promotions", "Spam", "Other"]
)

# =================================================
# Display Emails
# =================================================
st.subheader("📨 Recent Emails")

if not emails:
    st.warning("No emails found.")
    st.stop()

for email in emails:
    category = classify_email(email)

    if category_filter != "All" and category != category_filter:
        continue

    # Badge color
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
