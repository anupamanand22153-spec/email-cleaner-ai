import os, sys, re, urllib.parse
from collections import Counter
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests as req_lib
import streamlit as st
from google.oauth2.credentials import Credentials

from app.auth.google_auth import get_google_auth_flow
from app.gmail2.gmail_service import get_gmail_service, fetch_email_metadata
from app.logic.email_classifier import classify_email

try:
    from app.database.user_repository import save_user, save_waitlist
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
    save_user = None
    save_waitlist = None

try:
    from app.ai.summarizer import summarize_and_extract, generate_daily_briefing
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

st.set_page_config(page_title="Email Cleaner AI", layout="wide")

# Session state defaults
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

# ── OAuth callback ──────────────────────────────────────────────────
query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated and not st.session_state.token_fetched:
    st.session_state.token_fetched = True
    try:
        token_data = req_lib.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": query_params["code"],
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "redirect_uri": st.secrets["google"]["redirect_uri"],
                "grant_type": "authorization_code",
            },
        ).json()
        if "error" in token_data:
            raise ValueError(token_data)

        creds = Credentials(
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

        st.session_state.credentials = creds
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

# ── Landing page (unauthenticated) ──────────────────────────────────
if not st.session_state.authenticated:

    # Hero
    st.markdown("""
<div style='text-align: center; padding: 2rem 0 1rem 0;'>
    <h1 style='font-size: 3rem; margin-bottom: 0.5rem;'>📧 Email Cleaner AI</h1>
    <p style='font-size: 1.3rem; color: #aaa;'>Your inbox, understood in seconds.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # Features
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown("### 📊\n**Inbox Dashboard**\nSee your emails broken down by category instantly.")
    col2.markdown("### 🤖\n**AI Summaries**\nGet a one-line summary of every email — no reading required.")
    col3.markdown("### 🚫\n**Unsubscribe Engine**\nSpot the top senders flooding your inbox.")
    col4.markdown("### 💾\n**Storage Stats**\nSee exactly which emails are eating your Gmail storage.")

    st.markdown("---")

    # Two columns: sign in + waitlist
    left, right = st.columns(2)

    with left:
        st.subheader("🔑 Already have access?")
        st.caption("Sign in with your Google account to launch the app.")
        flow = get_google_auth_flow()
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
        st.markdown(f"### [👉 Sign in with Google]({auth_url})")
        st.caption("🔒 Read-only access — we never delete or modify your emails.")

    with right:
        st.subheader("✋ Want early access?")
        st.caption("Join the waitlist and we'll reach out when a spot opens.")
        with st.form("waitlist_form"):
            w_name  = st.text_input("Your name")
            w_email = st.text_input("Your email")
            submitted = st.form_submit_button("Request Access", use_container_width=True)

        if submitted:
            if not w_email or "@" not in w_email:
                st.error("Please enter a valid email address.")
            elif DB_AVAILABLE and save_waitlist:
                try:
                    save_waitlist(email=w_email.strip(), name=w_name.strip())
                    st.success(f"✅ You're on the list, {w_name or 'friend'}! We'll be in touch.")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
            else:
                st.warning("Database unavailable — please try again later.")

    st.stop()

# ── Save user to DB (silent) ─────────────────────────────────────────
if DB_AVAILABLE and not st.session_state.user_saved:
    try:
        save_user(email=st.session_state.user_email, full_name=st.session_state.user_name, provider="google")
        st.session_state.user_saved = True
    except Exception:
        pass

# ── Load & cache emails ──────────────────────────────────────────────
def load_emails():
    if "cached_classified" not in st.session_state:
        service = get_gmail_service(st.session_state.credentials)
        with st.spinner("Loading your inbox..."):
            emails = fetch_email_metadata(service, max_results=100)
        st.session_state.cached_classified = [(e, classify_email(e)) for e in emails]
    return st.session_state.cached_classified

# ── Sidebar navigation ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 📧 Email Cleaner AI")
    st.markdown(f"👤 **{st.session_state.user_name}**")
    st.caption(st.session_state.user_email)
    st.divider()
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "📨 Inbox", "🚫 Unsubscribe", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Helper ───────────────────────────────────────────────────────────
def format_size(b):
    if b >= 1_000_000_000: return f"{b/1_000_000_000:.2f} GB"
    if b >= 1_000_000:     return f"{b/1_000_000:.1f} MB"
    if b >= 1_000:         return f"{b/1_000:.1f} KB"
    return f"{b} B"

# ════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    classified = load_emails()
    st.title("📊 Dashboard")
    st.caption(f"Stats for your last {len(classified)} emails")

    # ── Daily AI Briefing ──────────────────────────────────────────
    if AI_AVAILABLE:
        if "daily_briefing" not in st.session_state:
            with st.spinner("✨ Generating your daily briefing..."):
                st.session_state.daily_briefing = generate_daily_briefing(
                    st.session_state.user_name, classified
                )
        st.info(st.session_state.daily_briefing)
        st.divider()

    # Email counts
    st.subheader("📬 Inbox Summary")
    counts = Counter(cat for _, cat in classified)
    for cat in ["Important", "Promotions", "Spam", "Other"]:
        counts.setdefault(cat, 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Important", counts["Important"])
    c2.metric("🟡 Promotions", counts["Promotions"])
    c3.metric("🔴 Spam", counts["Spam"])
    c4.metric("⚪ Other", counts["Other"])

    st.bar_chart(pd.DataFrame(
        {"Emails": [counts[c] for c in ["Important", "Promotions", "Spam", "Other"]]},
        index=["Important", "Promotions", "Spam", "Other"]
    ), color="#4F8BF9")

    st.divider()

    # Storage
    st.subheader("💾 Storage Usage")
    size_by_cat = {"Important": 0, "Promotions": 0, "Spam": 0, "Other": 0}
    for email, cat in classified:
        size_by_cat[cat] += email.get("sizeEstimate", 0)
    total = sum(size_by_cat.values())

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("🟢 Important",  format_size(size_by_cat["Important"]))
    s2.metric("🟡 Promotions", format_size(size_by_cat["Promotions"]))
    s3.metric("🔴 Spam",       format_size(size_by_cat["Spam"]))
    s4.metric("⚪ Other",      format_size(size_by_cat["Other"]))

    st.bar_chart(pd.DataFrame(
        {"Size (MB)": [round(size_by_cat[c] / 1_000_000, 2) for c in ["Important", "Promotions", "Spam", "Other"]]},
        index=["Important", "Promotions", "Spam", "Other"]
    ), color="#F97B4F")
    st.caption(f"Total estimated: **{format_size(total)}** across last {len(classified)} emails")

# ════════════════════════════════════════════════════════════════════
# PAGE: Inbox
# ════════════════════════════════════════════════════════════════════
elif page == "📨 Inbox":
    classified = load_emails()
    st.title("📨 Inbox Analysis")
    st.caption(f"Your last {len(classified)} emails")

    category_filter = st.selectbox("Filter by category:", ["All", "Important", "Promotions", "Spam", "Other"])
    filtered = [(e, cat) for e, cat in classified if category_filter == "All" or cat == category_filter]

    BADGES = {"Important": "🟢 IMPORTANT", "Promotions": "🟡 PROMOTION", "Spam": "🔴 SPAM", "Other": "⚪ OTHER"}

    st.markdown(f"**{len(filtered)} emails** in this view")
    st.divider()

    # ── Load AI summaries + actions (first 30 emails, cached) ─────
    if AI_AVAILABLE:
        if "ai_summaries" not in st.session_state:
            emails_to_analyse = [e for e, _ in classified[:30]]
            with st.spinner("✨ AI is reading your emails..."):
                summaries, actions = summarize_and_extract(emails_to_analyse)
            st.session_state.ai_summaries = summaries
            st.session_state.ai_actions   = actions

        summaries = st.session_state.ai_summaries
        actions   = st.session_state.ai_actions
    else:
        summaries = [None] * len(classified)
        actions   = [None] * len(classified)

    # Build index map from original position
    classified_with_idx = [(i, e, cat) for i, (e, cat) in enumerate(classified)]

    if not filtered:
        st.info(f"No emails in category: {category_filter}")
    else:
        filtered_with_idx = [(i, e, cat) for i, e, cat in classified_with_idx
                             if category_filter == "All" or cat == category_filter]
        for i, email, category in filtered_with_idx:
            col1, col2 = st.columns([5, 1])
            col1.markdown(f"**{email.get('Subject', '(No Subject)')}**")
            col2.markdown(BADGES.get(category, "⚪ OTHER"))
            st.caption(f"From: {email.get('From', 'N/A')}  ·  {email.get('Date', '')}")

            if i < len(summaries) and summaries[i]:
                st.markdown(f"> {summaries[i]}")
            if i < len(actions) and actions[i]:
                st.warning(f"⚠️ **Action:** {actions[i]}")
            st.divider()

# ════════════════════════════════════════════════════════════════════
# PAGE: Unsubscribe
# ════════════════════════════════════════════════════════════════════
elif page == "🚫 Unsubscribe":
    classified = load_emails()
    st.title("🚫 Unsubscribe Suggestions")
    st.info("🔒 Read-only — use the unsubscribe link inside each email to opt out.")

    def extract_sender(from_header):
        m = re.match(r'^"?([^"<]+)"?\s*<', from_header)
        if m: return m.group(1).strip()
        m2 = re.search(r'[\w.+\-]+@[\w\-]+\.[a-zA-Z]+', from_header)
        if m2: return m2.group(0)
        return from_header.strip()

    promo_emails = [e for e, cat in classified if cat == "Promotions"]

    if not promo_emails:
        st.success("No promotional emails found. Your inbox looks clean!")
    else:
        sender_counts = Counter(extract_sender(e.get("From", "Unknown")) for e in promo_emails)
        top_senders = sender_counts.most_common(15)
        total_promo = len(promo_emails)

        st.markdown(f"Found **{total_promo} promotional emails** from **{len(sender_counts)} senders**")
        st.divider()

        h1, h2, h3 = st.columns([1, 5, 2])
        h1.markdown("**#**"); h2.markdown("**Sender**"); h3.markdown("**Emails**")
        st.divider()

        for i, (sender, count) in enumerate(top_senders, 1):
            pct = round(count / total_promo * 100)
            c1, c2, c3 = st.columns([1, 5, 2])
            c1.markdown(f"{i}")
            c2.markdown(f"**{sender}**")
            c3.markdown(f"🟡 {count}  `{pct}%`")

# ════════════════════════════════════════════════════════════════════
# PAGE: Settings
# ════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("👤 Account")
    st.markdown(f"**Name:** {st.session_state.get('user_name', 'N/A')}")
    st.markdown(f"**Email:** {st.session_state.get('user_email', 'N/A')}")
    st.markdown("**Provider:** Google")

    st.divider()

    st.subheader("🔄 Refresh Data")
    st.caption("Emails are cached for your session. Click to reload from Gmail.")
    if st.button("Refresh Inbox Data"):
        for key in ["cached_classified", "ai_summaries", "ai_actions", "daily_briefing"]:
            st.session_state.pop(key, None)
        st.success("Cache cleared — go to Dashboard or Inbox to reload.")
