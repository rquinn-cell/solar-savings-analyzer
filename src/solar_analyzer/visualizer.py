import pandas as pd
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def load_data(json_path='data/bill_history_clean.json'):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Flatten the JSON for Pandas
    rows = []
    for entry in data:
        rows.append({
            'date': entry['statement_date'],
            'total_due': entry['financials']['total_due'],
            'bank_balance': entry['financials']['bank_dollar_balance'],
            'delivered_on': entry['usage_delivered']['on_peak'],
            'delivered_off': entry['usage_delivered']['off_peak'],
            'received_on': entry['usage_received']['on_peak'],
            'received_off': entry['usage_received']['off_peak']
        })
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date')

def create_dashboard():
    df = load_data()
    
    # Create subplots: 1. Energy Balance, 2. Financials
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Net Energy Flow (kWh)", "Solar Bank & Monthly Cost ($)")
    )

    # --- CHART 1: Energy (Usage vs Generation) ---
    fig.add_trace(
        go.Bar(name='Used (Delivered)', x=df['date'], y=df['delivered_on'] + df['delivered_off'], marker_color='red'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='Made (Received)', x=df['date'], y=-(df['received_on'] + df['received_off']), marker_color='green'),
        row=1, col=1
    )

    # --- CHART 2: Financials (Bank Balance & Bills) ---
    fig.add_trace(
        go.Scatter(name='Bank Balance', x=df['date'], y=df['bank_balance'], mode='lines+markers', line=dict(color='blue', width=4)),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(name='Monthly Bill', x=df['date'], y=df['total_due'], marker_color='orange'),
        row=2, col=1
    )

    # Layout styling
    fig.update_layout(
        title='Solar Performance Dashboard',
        barmode='relative', # Stacks positive/negative bars
        height=800,
        template='plotly_white'
    )
    
    fig.show()

if __name__ == "__main__":
    create_dashboard()