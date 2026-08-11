import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Service Role Key bypasses RLS policies for admin scripts
supabase = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

SOURCE_USER = "9ef12022-7e9f-4013-96a3-f97716e4c2da"
DEMO_USER = "f98b28b9-7a38-4342-8494-3ca5976cefb4"

# 1. Fetch source rows
source_data = supabase.table("bill_history").select("*").eq("user_id", SOURCE_USER).execute().data

# 2. Re-assign user_id and strip primary key 'id' to allow fresh inserts
demo_rows = []
for row in source_data:
    new_row = row.copy()
    new_row.pop("id", None)  # Remove primary key ID so Supabase generates a new one
    new_row["user_id"] = DEMO_USER
    demo_rows.append(new_row)

# 3. Batch insert into demo profile
if demo_rows:
    supabase.table("bill_history").insert(demo_rows).execute()
    print(f"Successfully cloned {len(demo_rows)} bill records to Demo User {DEMO_USER}")