import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Initialize connection using secrets
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def save_bills_to_history(user_id, bill_lists):
    """
    Saves multiple scrubbed bill rows to Supabase.
    bill_lists is a list of dicts from your app.py all_rows list.
    """
    supabase = get_supabase_client()
    
    # We map your DataFrame/Dict columns to the SQL table names
    data = []
    for bill_row in bill_lists:
        data.append({
            "user_id": user_id,
            "statement_date": bill_row['Date'].strftime('%Y-%m-%d'),
            "usage_on_peak": bill_row['Usage_On_Peak'],
            "usage_off_peak": bill_row['Usage_Off_Peak'],
            "gen_on_peak": bill_row['Gen_On_Peak'],
            "gen_off_peak": bill_row['Gen_Off_Peak'],
            "actual_bill": bill_row['Actual_Bill'],
            "shadow_bill": bill_row['Shadow_Bill'],
            "monthly_savings": bill_row['Monthly_Savings'],
            "monthly_bank_contrib": bill_row['Monthly_Bank_Contrib'],
            "bank_balance": bill_row['Bank_Balance'],
            "on_peak_rate": bill_row.get('On_Peak_Rate'),
            "off_peak_rate": bill_row.get('Off_Peak_Rate')
        })
    
    # Upsert: If (user_id, statement_date) exists, update. Otherwise, insert.
    # This relies on the UNIQUE constraint we set in the SQL setup.
    result = supabase.table("bill_history").upsert(
        data, 
        on_conflict="user_id, statement_date"
    ).execute()
    
    return result

def fetch_user_history(user_id):
    """Fetches all scrubbed bills for a specific user."""
    supabase = get_supabase_client()
    response = supabase.table("bill_history")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("statement_date")\
        .execute()
    return response.data

def fetch_system_cost(user_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table("profiles")\
            .select("system_cost")\
            .eq("id", user_id)\
            .single()\
            .execute()
        
        # Guard check: Ensure we have actual data back
        if not response or not hasattr(response, 'data') or not response.data:
            return None
            
        data = response.data
        
        # Scenario A: Supabase returned a list of dictionaries (Standard Behavior)
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return data[0].get('system_cost')
            return None
            
        # Scenario B: Supabase returned a single dictionary directly
        if isinstance(data, dict):
            return data.get('system_cost')
            
        return None    

    except Exception as e:
        # Deliberately extract raw details from the Supabase exception object
        import traceback
        print("--- COMPLETE LOG RECOVERY STACK ---")
        traceback.print_exc()
        print(f"Details: {repr(e)}")
        return None
#        print(f"Error fetching system cost for user {user_id}: {e}")
#        return None
    
def update_system_cost(user_id: str, user_email: str, system_cost: float):
    """
    Updates or inserts the total system cost for a given user in the profiles table.
    And creates the profile if it doesn't exist yet. This allows us to persist the user's system cost
    """
    supabase = get_supabase_client()
    
    try:
        current_time = datetime.utcnow().isoformat()

        payload = {
            "id": user_id,
            "system_cost": float(system_cost),
            "user_email": user_email,
            "updated_at": current_time
        }

        # We use upsert so it handles both new accounts and modifications seamlessly
        result = supabase.table("profiles").upsert(
            payload,
            on_conflict="id"
        ).execute()
    
        return result

    except Exception as e:
        print(f"Profile error: Failed to save profile for {user_email}: {e}")

def log_analytics_event(event_type: str, user_uuid: str = "ANONYMOUS", user_email: str = "Anonymous Sandbox"):
    """
    Logs an application telemetry heartbeat event directly to Supabase.
    Bypasses implicit SELECT queries using returning='minimal' to prevent RLS read blockages.
    """

    supabase = get_supabase_client()

    try:
        payload = {
            "event_type": event_type,
            "user_uuid": user_uuid,
            "user_email": user_email
        }
        
        # 'returning="minimal"' instructs Postgrest not to send a RETURNING * clause,
        # completely preventing post-insert read crashes.
        supabase.table("site_metrics").insert(payload, returning="minimal").execute()
        
    except Exception as e:
        # Graceful logging so background telemetry failures never crash the user's UI
        print(f"Telemetry warning: Failed to log event '{event_type}': {e}")