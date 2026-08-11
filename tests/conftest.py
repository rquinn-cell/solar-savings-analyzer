# tests/conftest.py
import os
import pytest
from supabase import create_client, Client

@pytest.fixture(scope="session")
def supabase_url():
    # Fallback to your production reference if environment variables aren't set
    return os.getenv("SUPABASE_URL", "https://hhwhkgoxdiqgdsassqom.supabase.co")

@pytest.fixture(scope="session")
def supabase_anon_key():
    # Retrieve the public anon key from your environment
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not anon_key:
        pytest.skip("SUPABASE_ANON_KEY environment variable not set.")
    return anon_key

@pytest.fixture(scope="session")
def supabase_anon_client(supabase_url, supabase_anon_key) -> Client:
    """Returns an unauthenticated Supabase client instance for testing RLS."""
    return create_client(supabase_url, supabase_anon_key)