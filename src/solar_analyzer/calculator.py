from decimal import Decimal
from .models import XcelSolarBill, EnergyUsage

class SolarSavingsCalculator:
    def __init__(self, bill: XcelSolarBill):
        self.bill = bill
        self.RATE_ON_PEAK = bill.on_peak_rate
        self.RATE_OFF_PEAK = bill.off_peak_rate
        self.RATE_CEPR_FS = bill.cepr_fs_rate
        
        # 1. Actual CEPR cost
        self.actual_cepr_cost = self.bill.cepr_fs_kwh * self.RATE_CEPR_FS
        
        # 2. Net energy cost billed by Xcel for energy consumed
        actual_net_energy_only = (
            (self.bill.net_usage.on_peak_kwh * self.RATE_ON_PEAK) +
            (self.bill.net_usage.off_peak_kwh * self.RATE_OFF_PEAK)
        )
        
        # 3. Reconstruct Gross Electric Service Charges (Before bank credits)
        # If monthly_bank_contribution is negative, add its absolute value back to get the baseline bill.
        gross_electric_bill = self.bill.total_electric_due
        if self.bill.monthly_bank_contribution < Decimal("0.00"):
            gross_electric_bill += abs(self.bill.monthly_bank_contribution)

        # 4. Fixed Residue = Baseline Charges - Net Energy - CEPR
        # This accurately isolates Service & Facility fees ($7.10) + riders/taxes
        self.fixed_residue = gross_electric_bill - actual_net_energy_only - self.actual_cepr_cost

    def calculate_shadow_cost(self) -> Decimal:
        """
        Calculates what the bill would have been if NO solar was produced.
        Shadow = (Gross Delivered kWh * Rates) + (Original CEPR) + (Original Fixed Fees)
        """
        gross_energy_cost = (
            (self.bill.delivered_by_xcel.on_peak_kwh * self.RATE_ON_PEAK) +
            (self.bill.delivered_by_xcel.off_peak_kwh * self.RATE_OFF_PEAK)
        )
        
        return (gross_energy_cost + self.actual_cepr_cost + self.fixed_residue).quantize(Decimal("0.01"))

    def estimate_monthly_savings(self) -> Decimal:
        """
        Pure dollar value saved this month by solar production + bank credits drawn.
        Savings = Shadow Bill - Net Out-of-Pocket Electric Paid
        """
        return self.calculate_shadow_cost() - self.bill.total_electric_due

    def get_monthly_roi_data(self):
        shadow = self.calculate_shadow_cost()
        actual = self.bill.total_electric_due
        savings = shadow - actual
        
        return {
            "shadow_bill": float(shadow),
            "actual_bill": float(actual),
            "monthly_savings": float(savings),
            "monthly_bank_contrib": float(self.bill.monthly_bank_contribution),
            "bank_balance": float(self.bill.rollover_bank_balance)
        }