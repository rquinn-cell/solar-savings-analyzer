import json
import os
from decimal import Decimal
from datetime import datetime
from src.solar_analyzer.models import XcelSolarBill, EnergyUsage
from src.solar_analyzer.calculator import SolarSavingsCalculator

def test_scrubbed_data_integrity_and_calculator():
    """
    Verifies that the scrubbed JSON data is valid and can be 
    used to reconstruct the model and run calculations on CI.
    """
    json_path = "data/bill_history_clean.json"
    
    # 1. Verify file exists in the repository
    assert os.path.exists(json_path), f"JSON data file missing at {json_path}"
    
    with open(json_path, "r") as f:
        data = json.load(f)
    
    assert len(data) > 0, "The JSON data file is empty."
    
    # 2. Test reconstruction for the most recent bill
    entry = data[-1]
    
    bill = XcelSolarBill(
        account_number="SCRUBBED",
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
    
    # 3. Verify the Calculator can process this 'Public' bill
    calc = SolarSavingsCalculator(bill)
    shadow = calc.calculate_shadow_cost()
    savings = calc.estimate_monthly_savings()
    
    # Basic sanity checks
    assert shadow >= bill.total_electric_due, "Shadow bill cannot be less than actual bill"
    assert savings >= 0, "Savings cannot be negative"