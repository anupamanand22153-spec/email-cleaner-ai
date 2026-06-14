import os, sys
from collections import Counter
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.gmail2.gmail_service import get_gmail_service, fetch_email_metadata
from app.logic.email_classifier import classify_email

st.set_page_config(page_title="Dashboard — Email Cleaner AI", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.page_link("main.py", label="Go to Sign In →")
    st.stop()

def format_size(b):
    if b >= 1_000_000_000: return f"{b/1_000_000_000:.2f} GB"
    if b >= 1_000_000: return f"{b/1_000_000:.1f} MB"
    if b >= 1_000: return f"{b/1_000:.1f} KB"
    return f"{b} B"

def load_emails():
    if "cached_classified" not in st.session_state:
        service = get_gmail_service(st.session_state.credentials)
        with st.spinner("Loading your inbox..."):
            emails = fetch_email_metadata(service, max_results=100)
        st.session_state.cached_classified = [(e, classify_email(e)) for e in emails]
    return st.session_state.cached_classified

classified = load_emails()

st.title("📊 Inbox Dashboard")
st.caption(f"Showing stats for your last {len(classified)} emails · {st.session_state.user_email}")

# --- Email Counts ---
st.subheader("📬 Inbox Summary")
counts = Counter(cat for _, cat in classified)
for cat in ["Important", "Promotions", "Spam", "Other"]:
    counts.setdefault(cat, 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🟢 Important", counts["Important"])
c2.metric("🟡 Promotions", counts["Promotions"])
c3.metric("🔴 Spam", counts["Spam"])
c4.metric("⚪ Other", counts["Other"])

chart_df = pd.DataFrame(
    {"Emails": [counts[c] for c in ["Important", "Promotions", "Spam", "Other"]]},
    index=["Important", "Promotions", "Spam", "Other"],
)
st.bar_chart(chart_df, color="#4F8BF9")

st.divider()

# --- Storage Stats ---
st.subheader("💾 Storage Usage")
size_by_cat = {"Important": 0, "Promotions": 0, "Spam": 0, "Other": 0}
for email, cat in classified:
    size_by_cat[cat] += email.get("sizeEstimate", 0)

total = sum(size_by_cat.values())
s1, s2, s3, s4 = st.columns(4)
s1.metric("🟢 Important", format_size(size_by_cat["Important"]))
s2.metric("🟡 Promotions", format_size(size_by_cat["Promotions"]))
s3.metric("🔴 Spam", format_size(size_by_cat["Spam"]))
s4.metric("⚪ Other", format_size(size_by_cat["Other"]))

size_df = pd.DataFrame(
    {"Size (MB)": [round(size_by_cat[c] / 1_000_000, 2) for c in ["Important", "Promotions", "Spam", "Other"]]},
    index=["Important", "Promotions", "Spam", "Other"],
)
st.bar_chart(size_df, color="#F97B4F")
st.caption(f"Total estimated: **{format_size(total)}** across last {len(classified)} emails")
