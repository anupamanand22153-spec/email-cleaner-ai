import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.supabase_client import get_supabase


def test_connection():
    try:
        supabase = get_supabase()

        print("✅ Connected to Supabase")

        return True

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()