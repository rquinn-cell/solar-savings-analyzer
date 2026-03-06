from decimal import Decimal
from .models import XcelSolarBill

class SolarSavingsCalculator:
    def __init__(self, bill: XcelSolarBill):
        self.bill = bill
        # Rates per January 2026 Bill
        self.RATE_ON_PEAK = Decimal("0.183310")
        self.RATE_OFF_PEAK = Decimal("0.067920")
        
        # Note: These are simplified; real bills include multi-line 
        # adjustments (Wildfire, Transmission, etc.)
        # We will refine these into a 'RateTable' object later.

    def calculate_shadow_cost(self) -> Decimal:
        """Calculates cost of GROSS energy delivered by Xcel."""
        on_pk = self.bill.delivered_by_xcel.on_peak_kwh * self.RATE_ON_PEAK
        off_pk = self.bill.delivered_by_xcel.off_peak_kwh * self.RATE_OFF_PEAK
        return (on_pk + off_pk).quantize(Decimal("0.01"))

    def estimate_monthly_savings(self, actual_electric_charges: Decimal) -> Decimal:
        """The difference between the Shadow Bill and what you actually paid."""
        return self.calculate_shadow_cost() - actual_electric_charges