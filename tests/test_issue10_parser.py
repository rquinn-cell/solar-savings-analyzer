import pytest
from decimal import Decimal
from src.solar_analyzer.parser import parse_xcel_pdf

import os
# This checks if the 'bills' folder exists
BILLS_EXIST = os.path.exists("bills/")
@pytest.mark.skipif(not BILLS_EXIST, reason="PDFs not available in this environment")
def test_july_30_bank_credit_parsing():
    """Verifies that negative monthly bank contributions (credits) parse correctly."""
    path = "bills/XcelBill-2026-07-30.pdf"
    bill = parse_xcel_pdf(path)
    
    # Assert monthly_bank_contribution is negative -$87.46
    assert bill.monthly_bank_contribution == Decimal("-87.46")
    
    # Assert rollover_bank_balance is $0.00
    assert bill.rollover_bank_balance == Decimal("0.00")
    
    # Assert total_electric_due reflects the credit applied ($99.87 - $87.46 = $12.41)
    assert bill.total_electric_due == Decimal("12.41")