from solar_analyzer.calculator import SolarSavingsCalculator
from solar_analyzer.models import XcelSolarBill, EnergyUsage # We will create these
from solar_analyzer.parser import parse_xcel_pdf
from solar_analyzer.calculator import SolarSavingsCalculator

path = "src/solar_analyzer/XcelBill-2026-01-02.pdf"
bill = parse_xcel_pdf(path)
calculator = SolarSavingsCalculator(bill)
print(f"Statement Date: {bill.statement_date}")
print(f"multiplier: {calculator.return_multiplier()}")

path = "src/solar_analyzer/XcelBill-2026-02-02.pdf"
bill = parse_xcel_pdf(path)
calculator = SolarSavingsCalculator(bill)
print(f"Statement Date: {bill.statement_date}")
print(f"multiplier: {calculator.return_multiplier()}")

path = "src/solar_analyzer/XcelBill-2026-03-03.pdf"
bill = parse_xcel_pdf(path)
calculator = SolarSavingsCalculator(bill)
print(f"Statement Date: {bill.statement_date}")
print(f"multiplier: {calculator.return_multiplier()}")

