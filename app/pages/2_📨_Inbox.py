import os, sys
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.gmail2.gmail_service import get_gmail_service, fetch_email_metadata
from app.logic.email_classifier import classify_email

st.set_page_config(page_title="Inbox — Email Cleaner AI", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.page_link("main.py", label="Go to Sign In →")
    st.stop()

def load_emails():
    if "cached_classified" not in st.session_state:
        service = get_gmail_service(st.session_state.credentials)
        with st.spinner("Loading your inbox..."):
            emails = fetch_email_metadata(service, max_results=100)
        st.session_state.cached_classified = [(e, classify_email(e)) for e in emails]
    return st.session_state.cached_classified

classified = load_emails()

st.title("📨 Inbox Analysis")
st.caption(f"Showing your last {len(classified)} emails · {st.session_state.user_email}")

category_filter = st.selectbox(
    "Filter by category:",
    ["All", "Important", "Promotions", "Spam", "Other"]
)

BADGES = {
    "Important": "🟢 IMPORTANT",
    "Promotions": "🟡 PROMOTION",
    "Spam": "🔴 SPAM",
    "Other": "⚪ OTHER",
}

filtered = [(e, cat) for e, cat in classified if category_filter == "All" or cat == category_filter]

st.markdown(f"**{len(filtered)} emails** in this view")
st.divider()

if not filtered:
    st.info(f"No emails in category: {category_filter}")
    st.stop()

for email, category in filtered:
    with st.container():
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"**{email.get('Subject', '(No Subject)')}**")
        col2.markdown(BADGES.get(category, "⚪ OTHER"))
        st.caption(f"From: {email.get('From', 'N/A')}  ·  {email.get('Date', '')}")
        st.divider()
