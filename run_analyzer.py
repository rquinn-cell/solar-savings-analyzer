# run_analyzer.py
import json
from decimal import Decimal
from datetime import datetime
from src.solar_analyzer.models import XcelSolarBill, EnergyUsage, SolarBankState
from src.solar_analyzer.calculator import SolarSavingsCalculator

def load_from_json(filepath="data/bill_history_clean.json"):
    with open(filepath, "r") as f:
        data = json.load(f)
    
    bills = []
    for entry in data:
        # Reconstruct the dataclass from JSON
        bill = XcelSolarBill(
            account_number="SCRUBBED", # PII removed
            statement_date=datetime.strptime(entry["statement_date"], "%Y-%m-%d").date(),
            service_start=datetime.strptime(entry["service_period"]["start"], "%Y-%m-%d").date(),
            service_end=datetime.strptime(entry["service_period"]["end"], "%Y-%m-%d").date(),
            delivered_by_xcel=EnergyUsage(
                on_peak_kwh=Decimal(str(entry["usage_delivered"]["on_peak"])),
                off_peak_kwh=Decimal(str(entry["usage_delivered"]["off_peak"]))
            ),
            delivered_by_customer=EnergyUsage(
                on_peak_kwh=Decimal(str(entry["usage_received"]["on_peak"])),
                off_peak_kwh=Decimal(str(entry["usage_received"]["off_peak"]))
            ),
            total_electric_due=Decimal(str(entry["financials"]["total_due"])),
            on_peak_rate=Decimal(str(entry["rates"]["on_peak"])),
            off_peak_rate=Decimal(str(entry["rates"]["off_peak"])),
            cepr_fs_rate=Decimal(str(entry["rates"]["cepr_fs"])),
            cepr_fs_kwh=Decimal(str(entry["cepr_usage"]))
        )
        bills.append(bill)
    return bills

def run_seasonal_analysis():
    bills = load_from_json()
    bank = SolarBankState(Decimal("0.00"), Decimal("0.00"))
    total_savings = Decimal("0.00")

    print(f"{'Date':<12} | {'Bank (On/Off)':<18} | {'Shadow':<10} | {'Actual':<8} | {'Savings':<8}")
    print("-" * 70)

    for bill in bills:
        calc = SolarSavingsCalculator(bill)
        shadow = calc.calculate_shadow_cost()
        actual = bill.total_electric_due
        savings = calc.estimate_monthly_savings()
        total_savings += savings
        
        bank = calc.calculate_new_bank_state(bank)
        bank_str = f"{bank.on_peak_kwh:>4.0f} / {bank.off_peak_kwh:>4.0f}"
        
        print(f"{str(bill.statement_date):<12} | {bank_str:<18} | ${shadow:>8.2f} | ${actual:>6.2f} | ${savings:>6.2f}")

    print("-" * 70)
    print(f"TOTAL SAVINGS: ${total_savings:.2f}")

if __name__ == "__main__":
    run_seasonal_analysis()
