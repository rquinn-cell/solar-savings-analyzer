# ☀️ Solar ROI Analyzer — Project Roadmap

This roadmap tracks the active engineering milestones, architectural refactors, and feature backlogs for the multi-tenant Xcel Energy utility tracking engine.

## 🚀 Active Milestone: Telemetry & Profile Traceability (Next Up)

### 🎯 Objective
Upgrade the database schemas and data-collection layers to inject plain-text email addresses and UUIDs directly into rows. This eliminates administrative ambiguity during log analysis, allowing immediate visual correlation between system metrics, system costs, and specific users without running manual table joins.

### 📋 Required Tasks

#### 1. Database Schema Alterations (Supabase SQL Editor)

- [ ] Modify site_metrics Table: Add explicit columns to capture session identities.

```sql
ALTER TABLE public.site_metrics 
ADD COLUMN user_uuid VARCHAR(255) DEFAULT 'ANONYMOUS',
ADD COLUMN user_email VARCHAR(255) DEFAULT 'Anonymous Sandbox';
```

- [ ] Modify profiles Table: Ensure username/email is explicitly captured alongside the UUID configuration.

```sql
ALTER TABLE public.profiles 
ADD COLUMN user_email VARCHAR(255) NOT NULL DEFAULT 'unassigned@example.com';
```

- [ ] Verify RLS Security Boundaries: Ensure that adding user_email columns does not alter row security rules. Confirm that `USING (auth.uid() = user_id)` (or matching UUID target) remains the primary hardware-enforced isolation shield.

#### 2. Codebase Refactoring (src/)

- [ ] Update Analytics Layer (database.py): Rewrite `log_analytics_event()` to accept and process user context strings:

```python
def log_analytics_event(event_type: str, user_uuid: str = "ANONYMOUS", user_email: str = "Anonymous Sandbox"):
    # Logic to pass both identifiers inside the insert dict payload
```

- [ ] Update Application Bootstrap (app.py): Pass `st.session_state.user_uuid` and `st.session_state.user_email` dynamically into the tracking heartbeat engine whenever the dashboard boots up or an operation fires.

- [ ] Update Profile Management Pipeline: Modify the logic that creates or updates profile data so it captures and saves the logged-in user's email address straight to the cloud row.

## 📈 Future Milestones & Feature Backlog

### Milestone: Infrastructure Optimization & Stability

- [ ] **Container Sleep Mitigation**: Set up a free automated cron ping worker (via UptimeRobot or Cron-Job.org) targeting the live deployment URL to bypass the Streamlit Community Cloud 3-day idling policy.

- [ ] **Graceful Socket Recovery**: Add code documentation or safe connection-handling routines to manage browser/server dropouts when client machines go to sleep overnight.

### Milestone: Dual-Commodity & Fuel-Switching Simulation

- [ ] **Parser Upgrades** (parser.py): Re-engineer the pdfplumber regex extraction pipeline to detect and isolate Xcel Energy natural gas data fields (Therms consumed, Gas Commodity service rates, and total monthly gas costs).

- [ ] **Gas History Storage Layer**: Build a `public.gas_history` database table mapping historical heating profiles back to specific accounts.

- [ ] **Heat Pump ROI Visualizer**: Build an interactive comparison dashboard mapping a gas furnace baseline against a cold-climate heat pump scenario utilizing dynamic COP (Coefficient of Performance) curve equations.

## 🏁 Completed Milestones

- [x] Migrate local user credentials engine to dynamic cloud-hosted Supabase Auth.
- [x] Configure and validate ironclad Row Level Security (RLS) tables to ensure multi-tenant database isolation.
- [x] Add "Use Anonymously" stateless sandbox profile selector to the login panel.
- [x] Clean up application interface layout by removing the legacy placeholder Privacy Toggle switch.
- [x] Separate developer testing libraries into requirements-dev.txt to optimize remote build processes.
- [x] Deploy stable application code globally onto Streamlit Community Cloud.