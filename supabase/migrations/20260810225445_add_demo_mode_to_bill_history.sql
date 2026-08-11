-- 1. Ensure RLS remains enabled on bill_history
ALTER TABLE public.bill_history ENABLE ROW LEVEL SECURITY;

-- 2. Drop the existing SELECT / ALL policy so we can re-create a unified policy
-- (Matching the exact name from your production snapshot)
DROP POLICY IF EXISTS "Enable individual user control for bill_history" ON public.bill_history;
DROP POLICY IF EXISTS "Enable select for users and demo mode" ON public.bill_history;

-- 3. Create a clean, dual-purpose SELECT policy
-- Grants read access to:
--   a) Authenticated users reading their own records
--   b) Anyone (including anon/demo sessions) reading the specific synthetic demo profile
CREATE POLICY "Enable select for users and demo mode"
ON public.bill_history
FOR SELECT
TO anon, authenticated
USING (
    (auth.role() = 'authenticated' AND auth.uid() = user_id)
    OR 
    (user_id = 'f98b28b9-7a38-4342-8494-3ca5976cefb4'::uuid)
);

-- 4. Re-apply the strict write policies (INSERT, UPDATE, DELETE) for authenticated owners
-- Explicitly guarding against writes to the demo UUID
DROP POLICY IF EXISTS "Enable write access for bill_history owners" ON public.bill_history;

CREATE POLICY "Enable write access for bill_history owners"
ON public.bill_history
FOR ALL
TO authenticated
USING (
    auth.uid() = user_id 
    AND user_id != 'f98b28b9-7a38-4342-8494-3ca5976cefb4'::uuid
)
WITH CHECK (
    auth.uid() = user_id 
    AND user_id != 'f98b28b9-7a38-4342-8494-3ca5976cefb4'::uuid
);