from solar_analyzer.parser import parse_xcel_pdf
from solar_analyzer.calculator import SolarSavingsCalculator
from solar_analyzer.models import SolarBankState
from decimal import Decimal

def run_seasonal_analysis(bill_paths):
    # Initialize our dual-bucket bank at zero
    bank = SolarBankState(Decimal("0.00"), Decimal("0.00"))
    total_savings = Decimal("0.00")

    print(f"{'Bill Date':<12} | {'Bank (On/Off)':<18} | {'Shadow Bill':<12} | {'Actual':<10} | {'Savings':<10}")
    print("-" * 75)

    for path in bill_paths:
        try:
            bill = parse_xcel_pdf(path)
            calc = SolarSavingsCalculator(bill)
            
            # Calculate financial metrics
            shadow = calc.calculate_shadow_cost()
            actual = bill.total_electric_due
            savings = calc.estimate_monthly_savings()
            total_savings += savings
            
            # Update Bank State for the next month
            # Note: In Winter, this will likely stay at 0/0
            bank = calc.calculate_new_bank_state(bank)
            
            # Format the bank string for display
            bank_str = f"{bank.on_peak_kwh:>4.0f} / {bank.off_peak_kwh:>4.0f} kWh"
            
            print(f"{str(bill.statement_date):<12} | {bank_str:<18} | ${shadow:>10.2f} | ${actual:>8.2f} | ${savings:>8.2f}")
            #print(f"DEBUG: {bill.statement_date} | CEPR Daily Factor: {bill.cepr_fs_kwh / bill.days_in_cycle:.2f}")
 
        except ValueError as e:
            print(f"SKIPPING {path}: {e}")
            continue # move to the next bill if we hit a parsing error or legacy bill

    print("-" * 75)
    print(f"{'TOTAL CUMULATIVE SAVINGS':<47} | ${total_savings:>8.2f}")

if __name__ == "__main__":
    # Add your 2-tier bills here in chronological order
    bills = [
        "src/solar_analyzer/XcelBill-2025-12-02.pdf",
        "src/solar_analyzer/XcelBill-2026-01-02.pdf",
        "src/solar_analyzer/XcelBill-2026-02-02.pdf",
        "src/solar_analyzer/XcelBill-2026-03-03.pdf"
    ]
    run_seasonal_analysis(bills)