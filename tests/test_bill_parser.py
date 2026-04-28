import pytest
from decimal import Decimal
from datetime import date
from src.solar_analyzer.calculator import SolarSavingsCalculator
from src.solar_analyzer.models import XcelSolarBill, EnergyUsage # We will create these
from src.solar_analyzer.parser import parse_xcel_pdf
from src.solar_analyzer.calculator import SolarSavingsCalculator

import os
# This checks if the 'bills' folder exists
BILLS_EXIST = os.path.exists("bills/")
@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_actual_pdf_parsing2026():
    path = "bills/XcelBill-2026-01-02.pdf"
    bill = parse_xcel_pdf(path)

    # Expected Data from Page 1 & 2 of your PDF
    expected_delivered_by_xcel_total = Decimal("1251.0") # 86 on-peak + 1165 off-peak
    expected_delivered_by_customer_total = Decimal("235.0") # 0 on-peak + 235 off-peak
    expected_net_on_peak = Decimal("86.0")
    expected_net_off_peak = Decimal("930.0")
    expected_total_electric_due = Decimal("155.67") # Combined Electric

    assert bill.delivered_by_xcel.total_kwh == expected_delivered_by_xcel_total
    assert bill.delivered_by_customer.total_kwh == expected_delivered_by_customer_total
    assert bill.net_usage.on_peak_kwh == expected_net_on_peak
    assert bill.net_usage.off_peak_kwh == expected_net_off_peak
    assert bill.statement_date == date(2026, 1, 2)
    assert bill.total_electric_due == expected_total_electric_due

@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_actual_pdf_parsing2025():
    path = "bills/XcelBill-2025-12-02.pdf"
    bill = parse_xcel_pdf(path)

    # Expected Data from Page 1 & 2 of your PDF
    expected_on_peak_delivered_by_xcel_total = Decimal("70.0")
    expected_off_peak_delivered_by_xcel_total = Decimal("836.0")
    expected_received_on_peak_total = Decimal("4.0")
    expected_received_off_peak_total = Decimal("377.0")
    expected_net_on_peak = Decimal("66.0")
    expected_net_off_peak = Decimal("459.0")
    expected_total_electric_due = Decimal("90.93") # Combined Electric
    expected_bank_dollar_balance = Decimal("0.00") # No bank balance reported on this bill

    assert bill.delivered_by_xcel.total_kwh == expected_on_peak_delivered_by_xcel_total + expected_off_peak_delivered_by_xcel_total
    assert bill.delivered_by_customer.total_kwh == expected_received_on_peak_total + expected_received_off_peak_total
    assert bill.net_usage.on_peak_kwh == expected_net_on_peak
    assert bill.net_usage.off_peak_kwh == expected_net_off_peak
    assert bill.statement_date == date(2025, 12, 2)
    assert bill.total_electric_due == expected_total_electric_due
    assert bill.rollover_bank_balance == expected_bank_dollar_balance

# put in test for 2026-04-02.pdf tp verify the bank balance parsing as well
@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_bank_balance_parsing():
    path = "bills/XcelBill-2026-04-02.pdf"
    bill = parse_xcel_pdf(path)

    expected_bank_dollar_balance = Decimal("24.19") # Example value, replace with actual from the bill
    expected_total_electric_due = Decimal("-15.72") # Example value, replace with actual from the bill
    assert bill.rollover_bank_balance == expected_bank_dollar_balance
    assert bill.total_electric_due == expected_total_electric_due

def test_savings_calculation_logic():
    # This represents what our parser SHOULD return
    sample_bill = XcelSolarBill(
        account_number="53-0012756531-8",
        statement_date=date(2026, 1, 2),
        service_start=date(2025, 11, 23),
        service_end=date(2025, 12, 25),
        delivered_by_xcel=EnergyUsage(on_peak_kwh=Decimal("86"), off_peak_kwh=Decimal("1165")),
        delivered_by_customer=EnergyUsage(on_peak_kwh=Decimal("0"), off_peak_kwh=Decimal("235")),
        rollover_bank_balance=Decimal("0.00"),
        total_electric_due=Decimal("155.67") # Combined Electric
    )

    calc = SolarSavingsCalculator(sample_bill)
    # Shadow cost for 86 On-Peak and 1165 Off-Peak
    # (86 * 0.183310) + (1165 * 0.067920) = ~94.89
    shadow = calc.calculate_shadow_cost()
    assert shadow > Decimal("90.00")

from src.solar_analyzer.scrubber import BillScrubber
@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_parsing_to_json_flow():
    # Use one of your 2026 PDFs as the source
    test_pdf = "bills/XcelBill-2026-03-03.pdf"
    bill = parse_xcel_pdf(test_pdf)
    scrubbed = BillScrubber.scrub(bill)
    
    # Assertions check if the JSON data matches the PDF extraction
    assert scrubbed["financials"]["total_due"] > 0
    assert "usage_delivered" in scrubbed
    # Ensure PII is gone
    assert "account_number" not in scrubbed
