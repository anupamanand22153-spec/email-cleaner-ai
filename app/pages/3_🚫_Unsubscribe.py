import os, sys, re
from collections import Counter
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.gmail2.gmail_service import get_gmail_service, fetch_email_metadata
from app.logic.email_classifier import classify_email

st.set_page_config(page_title="Unsubscribe — Email Cleaner AI", layout="wide")

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

def extract_sender_name(from_header):
    match = re.match(r'^"?([^"<]+)"?\s*<', from_header)
    if match:
        return match.group(1).strip()
    email_match = re.search(r'[\w.+\-]+@[\w\-]+\.[a-zA-Z]+', from_header)
    if email_match:
        return email_match.group(0)
    return from_header.strip()

classified = load_emails()

st.title("🚫 Unsubscribe Suggestions")
st.caption("Top senders filling your inbox with promotional emails")
st.info("🔒 This is a read-only view. To unsubscribe, click the unsubscribe link in the actual email.")

promo_emails = [e for e, cat in classified if cat == "Promotions"]

if not promo_emails:
    st.success("No promotional emails found in your last 100 emails. Your inbox looks clean!")
    st.stop()

sender_counts = Counter(extract_sender_name(e.get("From", "Unknown")) for e in promo_emails)
top_senders = sender_counts.most_common(15)

total_promo = len(promo_emails)
st.markdown(f"Found **{total_promo} promotional emails** from **{len(sender_counts)} senders**")
st.divider()

h1, h2, h3 = st.columns([1, 5, 2])
h1.markdown("**#**")
h2.markdown("**Sender**")
h3.markdown("**Emails**")
st.divider()

for i, (sender, count) in enumerate(top_senders, 1):
    pct = round(count / total_promo * 100)
    c1, c2, c3 = st.columns([1, 5, 2])
    c1.markdown(f"{i}")
    c2.markdown(f"**{sender}**")
    c3.markdown(f"🟡 {count} &nbsp;`{pct}%`")
