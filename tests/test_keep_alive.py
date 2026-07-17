import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

# We will implement these functions in src/solar_analyzer/database.py
# and app.py (or a utility module) as part of Issue #2 and Issue #3.
from src.solar_analyzer.database import log_ping_event

def test_log_ping_event_mocked():
    """
    Unit test to verify that log_ping_event formats the telemetry ping payload
    correctly and calls the Supabase client inserts without making real network requests.
    """
    with patch("src.solar_analyzer.database.get_supabase_client") as mock_get_client:
        # Create a mock chain for supabase.table("ping_log").insert(...).execute()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        
        mock_get_client.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        
        # Call our function
        log_ping_event(ping_source="cron-job.org", status="success")
        
        # Verify the database table targeted is "ping_log"
        mock_client.table.assert_called_with("ping_log")
        
        # Verify the insert payload format
        called_args, called_kwargs = mock_table.insert.call_args
        payload = called_args[0]
        
        assert payload["ping_source"] == "cron-job.org"
        assert payload["status"] == "success"
        assert "timestamp" in payload
        # Ensure timestamp is a valid ISO format string
        try:
            datetime.fromisoformat(payload["timestamp"])
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO format")
            
        assert called_kwargs.get("returning") == "minimal"
        mock_insert.execute.assert_called_once()


@pytest.mark.skipif(
    False,  # Default to skipped on CI. We can toggle this when SECRETS are present locally.
    reason="Requires live Supabase credentials in Streamlit secrets"
)
def test_log_ping_event_integration():
    """
    Integration test to verify actual table write permission (RLS) on the live dev database.
    """
    # This will hit the real database if secrets are configured
    try:
        log_ping_event(ping_source="pytest-integration-test", status="testing")
        # If it completes without raising an exception, the schema and RLS are configured perfectly!
    except Exception as e:
        pytest.fail(f"Integration test failed to write to live database: {e}")


def test_app_ping_router_bypasses_or_stops():
    """
    Simulates Streamlit query routing to ensure that the keep-alive hook in app.py
    intercepts with st.stop() when "?ping=" is passed, and executes normally otherwise.
    """
    with patch("streamlit.query_params") as mock_params, \
         patch("src.solar_analyzer.database.log_ping_event") as mock_log, \
         patch("streamlit.stop") as mock_stop, \
         patch("streamlit.set_page_config") as mock_page, \
         patch("src.solar_analyzer.auth.render_login_gate") as mock_gate:

        # Scenario A: Normal request (no ping query parameters)
        # Mocking query_params behaves like a dict without "ping"
        mock_params.__contains__.return_value = False
        mock_gate.return_value = "ANONYMOUS"

        # We manually import app.py to trigger execution flow
        import sys
        if "app" in sys.modules:
            del sys.modules["app"]
        import app  # noqa

        # Verify it skipped the ping logging and st.stop()
        mock_log.assert_not_called()
        mock_stop.assert_not_called()
        mock_gate.assert_called()  # It successfully proceeded to the login gate!

        # Scenario B: Keep-alive request (with "?ping=true&source=cron-job.org")
        mock_log.reset_mock()
        mock_stop.reset_mock()
        mock_gate.reset_mock()

        # Reset mock_gate call history so Scenario A's call doesn't pollute Scenario B's assertions
        mock_gate.reset_mock()

        # In real Streamlit, st.stop() raises an exception to halt script execution.
        # We simulate this behavior by raising a custom exception when mock_stop is called.
        mock_stop.side_effect = Exception("st.stop called")

        # Setup mock parameters containing "ping" and "source"
        mock_params.__contains__.side_effect = lambda key: key == "ping"
        # Avoid get side effect error by simulating dictionary style retrieval
        mock_params.get = MagicMock(side_effect=lambda key, default=None: "cron-job.org" if key == "source" else "true")

        # Re-trigger app.py execution
        if "app" in sys.modules:
            del sys.modules["app"]
        try:
            import app  # noqa
        except Exception as e:
            # We expect the mock st.stop() exception to be raised, halting the rest of app.py!
            assert str(e) == "st.stop called"
        # Verify the router caught the ping, logged it, and stopped processing the page
        mock_log.assert_called_once_with(ping_source="cron-job.org", status="success")
        mock_stop.assert_called_once()
        # Since the exception halted execution, render_login_gate was safely bypassed!
        mock_gate.assert_not_called()

