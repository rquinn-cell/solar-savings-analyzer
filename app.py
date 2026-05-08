import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.solar_analyzer.parser import parse_xcel_pdf
from src.solar_analyzer.calculator import SolarSavingsCalculator
from src.solar_analyzer.database import log_analytics_event
import tempfile
import os

# Page Config
st.set_page_config(page_title="Solar ROI Dashboard", layout="wide")

st.title("☀️ Xcel Solar ROI Analyzer")
st.markdown("Upload your Xcel PDFs to calculate true savings and monitor your Solar Bank.")

# 0. Analytics Heartbeat 
# We use session_state to ensure we only log ONCE per browser session
if 'analytics_logged' not in st.session_state:
    try:
        log_analytics_event("app_load")
        st.session_state.analytics_logged = True
        st.toast("Database Connected: Heartbeat Sent!") # Visual confirmation
    except Exception as e:
        st.error(f"Database Connection Failed: {e}")

# 1. Sidebar Configuration
with st.sidebar:
    st.header("Settings")
    uploaded_files = st.file_uploader(
        "Upload Xcel Bills (PDF)", 
        type="pdf", 
        accept_multiple_files=True
    )
    
    system_cost = st.number_input("Total System Cost ($)", value=15000, step=500)
    
    st.divider()
    privacy_mode = st.toggle("Privacy Mode", value=False, help="Redact metadata in the table view.")
    
    st.info("Files are processed in-memory and never stored.")

# 2. Processing Logic
if uploaded_files:
    all_rows = []
    
    with st.spinner(f"Analyzing {len(uploaded_files)} bills..."):
        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                bill_data = parse_xcel_pdf(tmp_path)
                # Calculator provides the Shadow Bill and Monthly Savings
                calc = SolarSavingsCalculator(bill_data)
                roi_stats = calc.get_monthly_roi_data()
                
                all_rows.append({
                    'Date': bill_data.statement_date,
                    'Actual_Bill': roi_stats['actual_bill'],
                    'Shadow_Bill': roi_stats['shadow_bill'],
                    'Monthly_Savings': roi_stats['monthly_savings'],
                    'Monthly_Bank_Contrib': roi_stats['monthly_bank_contrib'],
                    'Bank_Balance': roi_stats['bank_balance'],
                    'Usage_On_Peak': float(bill_data.delivered_by_xcel.on_peak_kwh),
                    'Usage_Off_Peak': float(bill_data.delivered_by_xcel.off_peak_kwh),
                    'Gen_On_Peak': float(bill_data.delivered_by_customer.on_peak_kwh),
                    'Gen_Off_Peak': float(bill_data.delivered_by_customer.off_peak_kwh)
                })
            except Exception as e:
                st.error(f"Error parsing {uploaded_file.name}: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    if all_rows:
        df = pd.DataFrame(all_rows).sort_values('Date')
        
        # Ensure column name matches the key used in all_rows
        df['Cumulative_Savings'] = df['Monthly_Savings'].cumsum()
        
        # 3. Top-Level Metrics
        current_bank = df['Bank_Balance'].iloc[-1]
        total_saved = df['Monthly_Savings'].sum()
        total_paid = df['Actual_Bill'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Solar Bank", f"${current_bank:,.2f}")
        m2.metric("Total Dollars Saved", f"${total_saved:,.2f}")
        m3.metric("Total Paid to Xcel", f"${total_paid:,.2f}")
        m4.metric("ROI Progress", f"{(total_saved / system_cost) * 100:.1f}%")

        # 4. Visualization Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Savings Growth", "Energy Balance", "Financial Data", "About & Legal"])

        from plotly.subplots import make_subplots

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

            st.plotly_chart(fig_savings, use_container_width=True)

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
            st.plotly_chart(fig_eng, use_container_width=True)

            st.divider() # Visual separator between energy and money

            # --- PLOT 2: Solar Bank Balance ($) ---
            st.subheader("Solar Bank Growth")
            
            # Data Prep: Calculate the previous balance to create a stacked effect
            chart_df = df.copy().sort_values("Date")
            # We subtract the monthly add from the balance to find what was carried over
            chart_df['Carryover_Balance'] = chart_df['Bank_Balance'] - chart_df['Monthly_Bank_Contrib']

            fig_bank = go.Figure()

            # Add the Carryover (Base)
            fig_bank.add_trace(go.Bar(
                x=chart_df['Date'],
                y=chart_df['Carryover_Balance'],
                name="Previous Balance",
                marker_color='#1f77b4', # Blue
                opacity=0.7
            ))

            # Add the New Monthly Addition
            fig_bank.add_trace(go.Bar(
                x=chart_df['Date'],
                y=chart_df['Monthly_Bank_Contrib'],
                name="New Monthly Credit",
                marker_color='#FFA15A', # Solar Orange
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
            st.plotly_chart(fig_bank, use_container_width=True)
            
            # Optional: Add a dynamic summary note
            current_bank = chart_df['Bank_Balance'].iloc[-1]
            last_add = chart_df['Monthly_Bank_Contrib'].iloc[-1]

            # Replace st.info with a clean metric row
            col1, col2 = st.columns(2)
            col1.metric("Total Bank Balance", f"${current_bank:,.2f}", delta=f"${last_add:,.2f}")
            col2.metric("Monthly Contribution", f"${last_add:,.2f}")

        with tab3:
            if privacy_mode:
                cols_to_hide = ['Account Number', 'Service Address', 'Statement Number']
                display_df = df.drop(columns=[c for c in cols_to_hide if c in df.columns])
            else:
                display_df = df
            
            st.dataframe(display_df, use_container_width=True)

        with tab4:
            st.header("Project Information")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🛠 Open Source")
                st.markdown("""
                This tool is open-source and built for the community.
                
                **GitHub:** [Source Code & Contributions](https://github.com/rquinn-cell/solar-savings-analyzer)  
                **License:** MIT License
                """)
                
            with col2:
                st.subheader("📈 Usage & Privacy")
                st.write("We track aggregate usage (number of bills parsed) to improve the tool.")
                st.write("Stateful accounts use **Scrubbed Storage**, meaning your name and address never leave your browser.")

            st.divider()
            st.subheader("Disclaimer")
            st.caption("""
            Estimates are based on extracted PDF data. Xcel Energy's billing cycles and rate 
            structures are complex; this tool should be used for personal estimation only. 
            Not affiliated with Xcel Energy.
            """)
            
            st.subheader("Legal Agreement")
            with st.expander("View Full License and Terms"):
                st.text("""
                Copyright (c) 2026 Richard Quinn
                
                Permission is hereby granted, free of charge, to any person obtaining a copy
                of this software and associated documentation files... (MIT License Text)
                """)

else:
    st.info("👈 Upload your Xcel Energy PDF bills in the sidebar to begin.")
