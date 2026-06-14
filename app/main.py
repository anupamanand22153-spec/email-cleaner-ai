# =================================================
# Ensure project root is on PYTHONPATH
# =================================================
import os
import sys
import re
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
# Storage Stats
# =================================================
st.subheader("💾 Storage Usage")
st.caption(f"Estimated across your last {len(emails)} emails")

def format_size(b):
    if b >= 1_000_000_000:
        return f"{b / 1_000_000_000:.2f} GB"
    if b >= 1_000_000:
        return f"{b / 1_000_000:.1f} MB"
    if b >= 1_000:
        return f"{b / 1_000:.1f} KB"
    return f"{b} B"

size_by_cat = {"Important": 0, "Promotions": 0, "Spam": 0, "Other": 0}
for email, category in classified:
    size_by_cat[category] += email.get("sizeEstimate", 0)

total_size = sum(size_by_cat.values())

s1, s2, s3, s4 = st.columns(4)
s1.metric("🟢 Important", format_size(size_by_cat["Important"]))
s2.metric("🟡 Promotions", format_size(size_by_cat["Promotions"]))
s3.metric("🔴 Spam", format_size(size_by_cat["Spam"]))
s4.metric("⚪ Other", format_size(size_by_cat["Other"]))

size_df = pd.DataFrame(
    {"Size (MB)": [round(size_by_cat[c] / 1_000_000, 2) for c in ["Important", "Promotions", "Spam", "Other"]]},
    index=["Important", "Promotions", "Spam", "Other"]
)
st.bar_chart(size_df, color="#F97B4F")

st.caption(f"Total estimated: **{format_size(total_size)}** across last {len(emails)} emails")

st.divider()

# =================================================
# Unsubscribe Suggestions
# =================================================
st.subheader("🚫 Top Promotional Senders")
st.caption("These senders are filling your inbox — consider unsubscribing")

def extract_sender_name(from_header):
    match = re.match(r'^"?([^"<]+)"?\s*<', from_header)
    if match:
        return match.group(1).strip()
    email_match = re.search(r'[\w.+\-]+@[\w\-]+\.[a-zA-Z]+', from_header)
    if email_match:
        return email_match.group(0)
    return from_header.strip()

promo_emails = [e for e, cat in classified if cat == "Promotions"]

if promo_emails:
    sender_counts = Counter(
        extract_sender_name(e.get("From", "Unknown")) for e in promo_emails
    )
    top_senders = sender_counts.most_common(10)

    header_col1, header_col2, header_col3 = st.columns([1, 4, 2])
    header_col1.markdown("**#**")
    header_col2.markdown("**Sender**")
    header_col3.markdown("**Emails**")
    st.divider()

    for i, (sender, count) in enumerate(top_senders, 1):
        c1, c2, c3 = st.columns([1, 4, 2])
        c1.markdown(f"{i}")
        c2.markdown(f"**{sender}**")
        c3.markdown(f"🟡 {count} emails")
else:
    st.info("No promotional emails found in your last 100 emails.")

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
