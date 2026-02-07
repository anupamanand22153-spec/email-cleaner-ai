from google_auth_oauthlib.flow import Flow
import streamlit as st
import os

def get_google_auth_flow():
    """
    Creates a Google OAuth flow with FIXED, CONSISTENT scopes
    """

    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    st.secrets["google"]["redirect_uri"]
                ],
            }
        },
        scopes=scopes,
        redirect_uri=st.secrets["google"]["redirect_uri"],
    )

    return flow
