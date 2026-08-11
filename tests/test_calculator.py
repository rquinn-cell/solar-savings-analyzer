import pytest
from decimal import Decimal
from src.solar_analyzer.parser import parse_xcel_pdf
from src.solar_analyzer.calculator import SolarSavingsCalculator

import os
# This checks if the 'bills' folder exists
BILLS_EXIST = os.path.exists("bills/")
@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_july_30_shadow_bill_and_savings():
    path = "bills/XcelBill-2026-07-30.pdf"
    bill = parse_xcel_pdf(path)
    calc = SolarSavingsCalculator(bill)
    
    roi_data = calc.get_monthly_roi_data()
    
    # 1. Shadow Bill without solar = $164.22
    assert roi_data["shadow_bill"] == 164.22
    
    # 2. Actual out-of-pocket electric paid = $12.41 ($99.87 - $87.46 credit)
    assert roi_data["actual_bill"] == 12.41
    
    # 3. Monthly Savings = $164.22 - $12.41 = $151.81
    assert roi_data["monthly_savings"] == 151.81