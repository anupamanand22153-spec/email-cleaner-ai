import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from app.database.supabase_client import get_supabase

st.title("Database Insert Test")

try:
    supabase = get_supabase()

    data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "provider": "google"
    }

    response = supabase.table("users").upsert(data, on_conflict="email").execute()

    st.success("✅ User inserted successfully")
    st.write("Response:", response.data)

except Exception as e:
    st.error(f"❌ Failed: {e}")
