from supabase import create_client
import streamlit as st


def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_key"]
    return create_client(url, key)


def get_supabase_public():
    """Use anon key for public/client-facing operations."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)