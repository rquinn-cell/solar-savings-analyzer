from decimal import Decimal
from datetime import date
from solar_analyzer.models import XcelSolarBill, EnergyUsage, SolarBankState
from solar_analyzer.calculator import SolarSavingsCalculator

def test_summer_surplus_banking():
    # Simulate a high-production month
    # House uses 300 total, Solar produces 800 total
    summer_bill = XcelSolarBill(
        account_number="53-0012756531-8",
        statement_date=date(2026, 7, 2),
        service_start=date(2026, 6, 1),
        service_end=date(2026, 7, 1),
        delivered_by_xcel=EnergyUsage(on_peak_kwh=Decimal("100"), off_peak_kwh=Decimal("200")),
        delivered_by_customer=EnergyUsage(on_peak_kwh=Decimal("300"), off_peak_kwh=Decimal("500")),
        rollover_bank_balance=Decimal("0.00"),
        total_electric_due=Decimal("15.00") # Just fixed fees
    )
    
    calc = SolarSavingsCalculator(summer_bill)
    initial_bank = SolarBankState(on_peak_kwh=Decimal("0.0"), off_peak_kwh=Decimal("0.0"))
    
    # Process the bill
    new_bank = calc.calculate_new_bank_state(initial_bank)
    
    # Assertions: 
    # On-Peak: 300 (Solar) - 100 (House) = 200 surplus
    # Off-Peak: 500 (Solar) - 200 (House) = 300 surplus
    assert new_bank.on_peak_kwh == Decimal("200")
    assert new_bank.off_peak_kwh == Decimal("300")

def test_bank_drain_logic():
    # Simulate a cloudy month where we drain a pre-existing bank
    cloudy_bill = XcelSolarBill(
        account_number="53-0012756531-8",
        statement_date=date(2026, 7, 2),
        service_start=date(2026, 6, 1),
        service_end=date(2026, 7, 1),
        delivered_by_xcel=EnergyUsage(on_peak_kwh=Decimal("100"), off_peak_kwh=Decimal("100")),
        delivered_by_customer=EnergyUsage(on_peak_kwh=Decimal("50"), off_peak_kwh=Decimal("50")),
        total_electric_due=Decimal("50.00")
    )
    
    calc = SolarSavingsCalculator(cloudy_bill)
    # Start with 40 On-Peak and 200 Off-Peak in the bank
    starting_bank = SolarBankState(on_peak_kwh=Decimal("40"), off_peak_kwh=Decimal("200"))
    
    # 1. New Bank State
    # On-Peak: (50-100) = -50. Bank was 40. 40 - 50 = -10 -> Floor to 0.0
    # Off-Peak: (50-100) = -50. Bank was 200. 200 - 50 = 150
    final_bank = calc.calculate_new_bank_state(starting_bank)
    assert final_bank.on_peak_kwh == Decimal("0.0")
    assert final_bank.off_peak_kwh == Decimal("150")
    
    # 2. Billed kWh (What Xcel actually charges you for)
    # On-Peak: Needed 50 net. Bank covered 40. Still owe for 10.
    # Off-Peak: Needed 50 net. Bank covered all 50. Owe 0.
    billed = calc.calculate_billed_kwh(starting_bank)
    assert billed.on_peak_kwh == Decimal("10")
    assert billed.off_peak_kwh == Decimal("0")
    