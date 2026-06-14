import os, sys
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

st.set_page_config(page_title="Settings — Email Cleaner AI", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.page_link("main.py", label="Go to Sign In →")
    st.stop()

st.title("⚙️ Settings")

# --- Account Info ---
st.subheader("👤 Account")
st.markdown(f"**Name:** {st.session_state.get('user_name', 'N/A')}")
st.markdown(f"**Email:** {st.session_state.get('user_email', 'N/A')}")
st.markdown(f"**Provider:** Google")

st.divider()

# --- Cache ---
st.subheader("🔄 Refresh Data")
st.caption("Emails are cached for your session. Click below to reload from Gmail.")
if st.button("🔃 Refresh Inbox Data"):
    for key in ["cached_classified", "cached_emails"]:
        st.session_state.pop(key, None)
    st.success("Cache cleared — navigate to Dashboard or Inbox to reload.")

st.divider()

# --- Sign Out ---
st.subheader("🚪 Sign Out")
if st.button("Sign Out", type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Signed out. Refresh the page to sign in again.")
    st.rerun()
