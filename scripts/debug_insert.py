import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Load environment context
load_dotenv()

# # Service Role Key bypasses RLS policies for admin scripts
# supabase = create_client(
#     os.getenv("SUPABASE_URL"), 
#     os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# )

SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
     print("❌ ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment!")
     sys.exit(1)

print(f"Connecting to Supabase at: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Target user UUIDs
DEMO_USER_ID = "f98b28b9-7a38-4342-8494-3ca5976cefb4"

# Sample payload from your January 2026 Xcel bill (Page 2)
payload = {
    "user_id": DEMO_USER_ID,
    "statement_date": "2026-01-02",
    "usage_on_peak": 86.0,
    "usage_off_peak": 1165.0,
    "gen_on_peak": 1016.0,
    "actual_bill": 155.67
}

try:
    print(f"Attempting insert into 'bill_history' for user {DEMO_USER_ID}...")
    
    # CRITICAL: Ensure .execute() is explicitly called at the end
    response = supabase.table("bill_history").insert(payload).execute()
    
    print("✅ INSERT SUCCESSFUL!")
    print("Response Data:", response.data)

except Exception as e:
    print("\n❌ INSERT FAILED WITH EXCEPTION:")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")