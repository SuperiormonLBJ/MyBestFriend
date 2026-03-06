"""
Shared Supabase client — import `supabase_client` from here throughout the project.
Uses the secret key so the backend can read/write all tables without RLS restrictions.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend/src (where the server runs from)
_env_path = Path(__file__).parent.parent / "src" / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

_url: str = os.environ["SUPABASE_URL"]
_key: str = os.environ["SUPABASE_SECRET_KEY"]

supabase_client: Client = create_client(_url, _key)
