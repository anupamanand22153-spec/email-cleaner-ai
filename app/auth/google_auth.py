from google_auth_oauthlib.flow import Flow
import streamlit as st


def get_google_auth_flow():
    """
    Create Google OAuth flow using Streamlit secrets.
    """

    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    client_config = {
        "web": {
            "client_id": st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                st.secrets["google"]["redirect_uri"]
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=scopes,
        redirect_uri=st.secrets["google"]["redirect_uri"],
    )

    return flow