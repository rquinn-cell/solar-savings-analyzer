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
            "on_peak_rate": bill_row.get('On_Rate'),
            "off_peak_rate": bill_row.get('Off_Rate')
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
    response = supabase.table("profiles")\
        .select("system_cost")\
        .eq("id", user_id)\
        .single()\
        .execute()
    return response.data['system_cost'] if response.data else 0

def update_system_cost(user_id: str, system_cost: float):
    """
    Updates or inserts the total system cost for a given user in the profiles table.
    """
    supabase = get_supabase_client()
    
    # We use upsert so it handles both new accounts and modifications seamlessly
    result = supabase.table("profiles").upsert(
        {
            "id": user_id, 
            "system_cost": float(system_cost)
        },
        on_conflict="id"
    ).execute()
    
    return result

def log_analytics_event(event_type):
    """Tracks non-PII events like 'app_load' or 'bill_parsed'."""
    supabase = get_supabase_client()
    supabase.table("site_metrics").insert({"event_type": event_type}).execute()