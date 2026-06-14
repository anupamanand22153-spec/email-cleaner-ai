from datetime import datetime, timezone
from app.database.supabase_client import get_supabase


def save_user(email: str, full_name: str, provider: str = "google"):
    """
    Insert user if new, or update last_login if they already exist.
    Returns the saved user record.
    """
    supabase = get_supabase()

    data = {
        "email": email,
        "full_name": full_name,
        "provider": provider,
        "last_login": datetime.now(timezone.utc).isoformat(),
    }

    response = (
        supabase.table("users")
        .upsert(data, on_conflict="email")
        .execute()
    )

    return response.data[0] if response.data else None
