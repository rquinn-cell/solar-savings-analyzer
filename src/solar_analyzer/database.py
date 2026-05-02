import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Initialize connection using secrets
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def save_bill_to_history(user_id, bill_row):
    """
    Saves a single scrubbed bill row to Supabase.
    bill_row is a dict from your app.py all_rows list.
    """
    supabase = get_supabase_client()
    
    # We map your DataFrame/Dict columns to the SQL table names
    data = {
        "user_id": user_id,
        "statement_date": bill_row['Date'].strftime('%Y-%m-%d'),
        "usage_on_peak": bill_row['Usage_On_Peak'],
        "usage_off_peak": bill_row['Usage_Off_Peak'],
        "gen_on_peak": bill_row['Gen_On_Peak'],
        "gen_off_peak": bill_row['Gen_Off_Peak'],
        "actual_bill": bill_row['Actual_Bill'],
        "shadow_bill": bill_row['Shadow_Bill'],
        "monthly_savings": bill_row['Monthly_Savings'],
        "bank_balance": bill_row['Bank_Balance'],
        "on_peak_rate": bill_row.get('On_Rate'),
        "off_peak_rate": bill_row.get('Off_Rate')
    }
    
    # upsert handles "Update if exists, Insert if new" based on user_id + date
    return supabase.table("bill_history").upsert(data).execute()

def load_user_history(user_id):
    """Fetches all scrubbed bills for a specific user."""
    supabase = get_supabase_client()
    response = supabase.table("bill_history").select("*").eq("user_id", user_id).order("statement_date").execute()
    return response.data

def log_analytics_event(event_type):
    """Tracks non-PII events like 'app_load' or 'bill_parsed'."""
    supabase = get_supabase_client()
    supabase.table("site_metrics").insert({"event_type": event_type}).execute()