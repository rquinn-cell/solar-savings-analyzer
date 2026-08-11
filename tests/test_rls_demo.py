# tests/test_rls_demo.py
from sys import exc_info

import pytest
from supabase import create_client

# Test unauthenticated / anon client access
def test_anon_client_can_read_demo_data(supabase_anon_client):
    response = (
        supabase_anon_client.table("bill_history")
        .select("*")
        .eq("user_id", "f98b28b9-7a38-4342-8494-3ca5976cefb4")
        .execute()
    )
    assert len(response.data) > 0, "Anon user should be able to read demo data."

def test_anon_client_cannot_write_demo_data(supabase_anon_client):
    with pytest.raises(Exception) as exc_info:
        supabase_anon_client.table("bill_history").insert({
            "user_id": "f98b28b9-7a38-4342-8494-3ca5976cefb4",
            "usage_on_peak": 86.0,
            "usage_off_peak": 1165.0
        }).execute()

    # Now exc_info holds the ExceptionInfo object with a .value attribute
    err_message = str(exc_info.value).lower()
    assert "new row violates row-level security policy" in err_message or "42501" in err_message
