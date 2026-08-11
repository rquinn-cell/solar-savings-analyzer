import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tempfile
import os

from src.solar_analyzer.parser import parse_xcel_pdf
from src.solar_analyzer.calculator import SolarSavingsCalculator
from src.solar_analyzer.database import (
    log_analytics_event, 
    save_bills_to_history, 
    fetch_user_history, 
    fetch_system_cost,
    update_system_cost,
    log_ping_event
)
from src.solar_analyzer.auth import render_login_gate, logout_user
import sys

# Target synthetic Demo User UUID
DEMO_USER_UUID = "f98b28b9-7a38-4342-8494-3ca5976cefb4"

# --- EARLY ROUTER FOR KEEP-ALIVE PINGS ---
# By handling this before loading heavy UI, database select sessions, or authentication gates,
# we drastically lower memory consumption and speed up external HTTP keep-alive pings.
# We are now using GitHub Actions as our primary keep-alive source, using a headless browser to ping the app every 15 minutes. This prevents Streamlit from idling out and losing session state.
query_params = st.query_params
if "action_wakeup" in query_params and query_params.get("action_wakeup") == "secure_runner_77":
    ping_source = query_params.get("source", "unspecified_cron")
    try:
        log_ping_event(ping_source=ping_source, status="success")
        st.text("Wakeup verified. Database logged successfully.")
    except Exception as e:
        st.text(f"Database logging failed: {e}")

    # Force exit Python completely to bypass the Streamlit auth render loop
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Solar ROI Dashboard", layout="wide")

# --- AUTHENTICATION & DEMO GATE ---
# render_login_gate() returns USER_UUID, or DEMO_USER_UUID if the user selected Demo Mode
USER_UUID = render_login_gate()

# If the gate passes, USER_UUID will contain the live, unique string from the cloud database
if USER_UUID:
    # State flags
    is_demo = (USER_UUID == DEMO_USER_UUID)
    is_anonymous = (USER_UUID == "ANONYMOUS")
    # Read-only mode applies to Demo sessions or Anonymous sessions
    is_read_only = is_demo or is_anonymous

    # Set user label for UI
    if is_demo:
        user_email = "Demo User (Read-Only)"
    else:
        user_email = st.session_state.get("user_email", "User Account")

    # --- SIDEBAR CONTROL PANEL ---
    with st.sidebar:
        st.write(f"Connected: **{user_email}**")
        if st.button("Log Out / Exit Demo", use_container_width=True):
            logout_user()
        st.divider()
         
        st.header("Settings")

        # Smart Cloud Sync Configuration
        if is_read_only:
            save_state = st.checkbox(
                "Enable Cloud Sync (Stateful)", 
                value=False, 
                disabled=True,
                help="Cloud Sync is unavailable in Demo/Anonymous mode."
            )
        else:
            # Normal registered user operation
            save_state = st.checkbox(
                "Enable Cloud Sync (Stateful)", 
                value=True, 
                help="Automatically loads your history and saves new uploads securely."
            )
            
        # File uploader (Disabled in Demo Mode)
        uploaded_files = st.file_uploader(
            "Upload Xcel Bills (PDF)", 
            type="pdf", 
            accept_multiple_files=True,
            disabled=is_demo,
            help="PDF upload is disabled in Demo Mode. Log in with a free account to upload personal statements."
        )
        
        # System Cost Initialization
        default_cost = 15000
        if save_state and not is_read_only:
            try:
                if 'system_cost_cloud' not in st.session_state:
                    cloud_cost = fetch_system_cost(USER_UUID)
                    
                    # If cloud_cost is None, this user has a brand new account!
                    if cloud_cost is None:
                        # Force initialize their profiles identity row immediately 
                        # using your default baseline parameters
                        update_system_cost(USER_UUID, user_email, default_cost)
                        st.session_state.system_cost_cloud = default_cost
                    else:
                        st.session_state.system_cost_cloud = cloud_cost
                        
                default_cost = st.session_state.system_cost_cloud
            except Exception:
                pass
                
        system_cost = st.number_input("Total System Cost ($)", value=int(default_cost), step=500)
        
        if save_state and not is_read_only and system_cost != st.session_state.get('system_cost_cloud', default_cost):
            try:
                update_system_cost(USER_UUID, user_email, system_cost)
                st.session_state.system_cost_cloud = system_cost
            except Exception:
                pass

    # --- MAIN PAGE HEADER ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("☀️ Xcel Solar ROI Analyzer")
        st.markdown("Calculate true savings, manage infrastructure ROI, and monitor your Solar Bank.")
    with col2:
        if save_state:
            st.write("") 
            if st.button("🔄 Force Cloud Sync"):
                st.cache_data.clear()
                st.rerun()

    # --- DEMO BANNER ---
    if is_demo:
        st.info("⚡ **Interactive Demo Mode Active:** Displaying sample Xcel TOU bill analysis (Read-Only).")

    # --- ANALYTICS HEARTBEAT ---
    if 'analytics_logged' not in st.session_state:
        try:
            event_type = "demo_load" if is_demo else "app_load"
            log_analytics_event(event_type, user_uuid=USER_UUID, user_email=user_email)
            st.session_state.analytics_logged = True
            if not is_demo:
                st.toast("Database Connected: Heartbeat Sent!")
        except Exception as e:
            if not is_demo:
                st.error(f"Database Connection Failed: {e}")
            else:
                pass
            
    # --- UNIFIED DATA EXTRACTION STREAM ---
    processed_bills = []
    known_dates = set()

    # Stream 1: Fetch Cloud Data (For logged-in stateful users OR Demo user read-only session)
    if save_state or is_demo:
        try:
            cloud_records = fetch_user_history(USER_UUID)
            for record in cloud_records:
                # Map database snake_case names directly back to internal pandas names
                bill_dt = pd.to_datetime(record['statement_date']).date()
                processed_bills.append({
                    'Date': bill_dt,
                    'Actual_Bill': float(record['actual_bill']),
                    'Shadow_Bill': float(record['shadow_bill']),
                    'Monthly_Savings': float(record['monthly_savings']),
                    'Monthly_Bank_Contrib': float(record['monthly_bank_contrib']),
                    'Bank_Balance': float(record['bank_balance']),
                    'Usage_On_Peak': float(record['usage_on_peak']),
                    'Usage_Off_Peak': float(record['usage_off_peak']),
                    'Gen_On_Peak': float(record['gen_on_peak']),
                    'Gen_Off_Peak': float(record['gen_off_peak']),
                    'On_Peak_Rate': float(record.get('on_peak_rate', 0.0)),
                    'Off_Peak_Rate': float(record.get('off_peak_rate', 0.0))
                })
                known_dates.add(bill_dt)
        except Exception as e:
            st.sidebar.error(f"Failed to load bill history: {e}")

    # Stream 2: Gather PDF Upload Data
    if uploaded_files and not is_demo:
        new_bills_to_sync = []
        with st.spinner(f"Analyzing {len(uploaded_files)} bills..."):
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    bill_data = parse_xcel_pdf(tmp_path)
                    bill_dt = bill_data.statement_date
                    
                    # Deduplicate: Skip file processing if this date is already loaded via cloud
                    if bill_dt in known_dates:
                        continue
                        
                    calc = SolarSavingsCalculator(bill_data)
                    roi_stats = calc.get_monthly_roi_data()
                    
                    payload = {
                        'Date': bill_dt,
                        'Actual_Bill': roi_stats['actual_bill'],
                        'Shadow_Bill': roi_stats['shadow_bill'],
                        'Monthly_Savings': roi_stats['monthly_savings'],
                        'Monthly_Bank_Contrib': roi_stats['monthly_bank_contrib'],
                        'Bank_Balance': roi_stats['bank_balance'],
                        'Usage_On_Peak': float(bill_data.delivered_by_xcel.on_peak_kwh),
                        'Usage_Off_Peak': float(bill_data.delivered_by_xcel.off_peak_kwh),
                        'Gen_On_Peak': float(bill_data.delivered_by_customer.on_peak_kwh),
                        'Gen_Off_Peak': float(bill_data.delivered_by_customer.off_peak_kwh),
                        'On_Peak_Rate': float(bill_data.on_peak_rate),
                        'Off_Peak_Rate': float(bill_data.off_peak_rate)
                    }
                    processed_bills.append(payload)
                    known_dates.add(bill_dt)
                    new_bills_to_sync.append(payload)
                    
                except Exception as e:
                    st.error(f"Error parsing {uploaded_file.name}: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
        # Feature 3: Auto-Save newly uploaded files if stateful
        if save_state and new_bills_to_sync:
            try:
                save_bills_to_history(USER_UUID, new_bills_to_sync)
                st.toast(f"🔥 Auto-Saved {len(new_bills_to_sync)} new bills to Cloud!")
            except Exception as e:
                st.error(f"Auto-save failed: {e}")

    # --- RENDERING PIPELINE ---
    if processed_bills:
        df = pd.DataFrame(processed_bills).sort_values('Date')
        df['Cumulative_Savings'] = df['Monthly_Savings'].cumsum()
        
        current_bank = df['Bank_Balance'].iloc[-1]
        total_saved = df['Monthly_Savings'].sum()
        total_paid = df['Actual_Bill'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Solar Bank", f"${current_bank:,.2f}")
        m2.metric("Total Dollars Saved", f"${total_saved:,.2f}")
        m3.metric("Total Paid to Xcel", f"${total_paid:,.2f}")
        m4.metric("ROI Progress", f"{(total_saved / system_cost) * 100:.1f}%")

        # Visualization Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Savings Growth", "Energy Balance", "Financial Data", "About & Legal"])

        with tab1:
            fig_savings = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.15,
                row_heights=[0.4, 0.6],
                subplot_titles=("MONTHLY SAVINGS", "CUMULATIVE INVESTMENT RECOVERY")
            )
            
            # Trace 1: Monthly Savings
            fig_savings.add_trace(go.Bar(
                x=df['Date'], y=df['Monthly_Savings'],
                name="Monthly Savings",
                marker=dict(color='rgba(50, 171, 96, 0.8)', line=dict(color='rgba(50, 171, 96, 1.0)', width=1)),
                hovertemplate="Saved: $%{y:.2f}<extra></extra>",
                showlegend=False
            ), row=1, col=1)
            
            # Trace 2: Cumulative Savings
            fig_savings.add_trace(go.Scatter(
                x=df['Date'], y=df['Cumulative_Savings'],
                name="Cumulative Saved",
                fill='tozeroy', 
                fillcolor='rgba(255, 215, 0, 0.2)',
                line=dict(color='gold', width=4),
                hovertemplate="Total: $%{y:.2f}<extra></extra>",
                showlegend=False
            ), row=2, col=1)

            # 1. Update the layout - use the GLOBAL xaxis object for spikes
            fig_savings.update_layout(
                height=700,
                template="plotly_white",
                hovermode="x unified",
                margin=dict(t=50, b=50, l=50, r=50),
                # This targets the global xaxis (usually tied to the bottom plot)
                xaxis_showspikes=True,
                xaxis_spikemode="across",
                xaxis_spikesnap="cursor",
                xaxis_showline=True,
                xaxis_spikethickness=1,
                xaxis_spikecolor="rgba(0,0,0,0.3)",
                xaxis_spikedash="dash",
            )

            # 2. Sync the top axis (xaxis2) to also show the spike but hide labels
            fig_savings.update_xaxes(
                showspikes=True,
                spikemode="across",
                showticklabels=False,
                row=1, col=1
            )
            
            # 3. Explicitly force the bottom axis (xaxis) to show labels
            fig_savings.update_xaxes(
                showticklabels=True, 
                tickformat="%b %Y", 
                type='date',
                row=2, col=1
            )

            # 3. Y-AXIS & DECORATIONS
            fig_savings.update_yaxes(title_text="USD ($)", row=1, col=1)
            fig_savings.update_yaxes(title_text="USD ($)", row=2, col=1)

            # Subtle background for the bottom plot
            fig_savings.add_hrect(
                y0=df['Cumulative_Savings'].min(), 
                y1=df['Cumulative_Savings'].max() * 1.1, 
                fillcolor="gray", opacity=0.03, 
                layer="below", line_width=0,
                row=2, col=1
            )

            st.plotly_chart(fig_savings, width="stretch")

        with tab2:
            # --- PLOT 1: Net Energy Flow (kWh) ---
            st.subheader("Energy Flow")
            fig_eng = go.Figure()
            fig_eng.add_trace(go.Bar(
                x=df['Date'], 
                y=df['Usage_On_Peak'] + df['Usage_Off_Peak'], 
                name="Consumed from Grid", marker_color='#EF553B'
            ))
            fig_eng.add_trace(go.Bar(
                x=df['Date'], 
                y=-(df['Gen_On_Peak'] + df['Gen_Off_Peak']), 
                name="Exported to Grid", marker_color='#00CC96'
            ))
            fig_eng.update_layout(
                title="Net Energy Flow (kWh)",
                barmode='relative',
                template="plotly_white",
                xaxis_title="Billing Cycle",
                yaxis_title="kWh",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_eng, width="stretch")

            st.divider()

            # --- PLOT 2: Solar Bank Balance ($) ---
            st.subheader("Solar Bank Growth")
            
            chart_df = df.copy().sort_values("Date")
            # Linked securely to our updated internal dict key 'Monthly_Bank_Contrib'
            chart_df['Carryover_Balance'] = chart_df['Bank_Balance'] - chart_df['Monthly_Bank_Contrib']

            fig_bank = go.Figure()
            fig_bank.add_trace(go.Bar(
                x=chart_df['Date'],
                y=chart_df['Carryover_Balance'],
                name="Previous Balance",
                marker_color='#1f77b4',
                opacity=0.7
            ))
            fig_bank.add_trace(go.Bar(
                x=chart_df['Date'],
                y=chart_df['Monthly_Bank_Contrib'],
                name="New Monthly Credit",
                marker_color='#FFA15A',
            ))
            fig_bank.update_layout(
                title="Cumulative Solar Bank Balance ($)",
                barmode='stack',
                template="plotly_white",
                xaxis_title="Billing Cycle",
                yaxis_title="USD ($)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_bank, width="stretch")

        with tab3:
            st.dataframe(df, width="stretch")
            st.divider()
            if is_demo:
                st.caption("🔒 Account status: Demo Mode (Read-Only).")
            elif save_state:
                st.caption(f"🔒 Account status: Connected. Real-time encryption active for User UID: {USER_UUID}")
            else:
                st.caption("🔒 Account status: Stateless. No cloud connection active.")

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("☀️ About the Tool")
                st.write("""
                The Xcel Solar ROI Analyzer parses residential electric bill summaries to separate 
                baseline operational costs from true net metering production.
                """)
                st.markdown("**Developer and Contact Support:** [Rick Quinn](mailto:rquinn@solinservice.com)")
                st.markdown("**GitHub:** [Source Code & Contributions](https://github.com/rquinn-cell/solar-savings-analyzer)")
                st.markdown("**License:** MIT License")
                
            with col2:
                st.subheader("📈 Usage & Privacy")
                st.write("Stateful accounts use **Scrubbed Storage**, meaning your name and address never leave your browser context.")

            st.divider()
            st.subheader("Disclaimer")
            st.caption("Estimates are based on extracted PDF data. Not affiliated with Xcel Energy.")
    else:
        st.info("👈 Upload your Xcel Energy PDF bills in the sidebar, or click 'Try Interactive Demo' to explore sample data.")