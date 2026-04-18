from decimal import Decimal
from .models import XcelSolarBill, EnergyUsage, SolarBankState

class SolarSavingsCalculator:
    def __init__(self, bill: XcelSolarBill):
        self.bill = bill
        self.RATE_ON_PEAK = bill.on_peak_rate
        self.RATE_OFF_PEAK = bill.off_peak_rate
        self.RATE_CEPR_FS = bill.cepr_fs_rate
        
        # FIXED FEE AUDIT:
        # We isolate the actual CEPR cost and 'other' fees to avoid
        # solar logic from accidentally 'saving' you money on fixed costs.
        self.actual_cepr_cost = self.bill.cepr_fs_kwh * self.RATE_CEPR_FS
        
        # Calculate what you paid for energy alone
        actual_net_energy_only = (
            (self.bill.net_usage.on_peak_kwh * self.RATE_ON_PEAK) +
            (self.bill.net_usage.off_peak_kwh * self.RATE_OFF_PEAK)
        )
        
        # Residue = Total Bill - Energy - CEPR
        # This captures Service Fee ($7.10) + Wildfire + Trans + etc.
        self.fixed_residue = self.bill.total_electric_due - actual_net_energy_only - self.actual_cepr_cost

    def calculate_shadow_cost(self) -> Decimal:
        """
        Calculates what the bill would have been if NO solar was produced.
        Shadow = (Gross kWh * Rates) + (Original CEPR) + (Original Fixed Fees)
        """
        gross_energy_cost = (
            (self.bill.delivered_by_xcel.on_peak_kwh * self.RATE_ON_PEAK) +
            (self.bill.delivered_by_xcel.off_peak_kwh * self.RATE_OFF_PEAK)
        )
        
        # We assume CEPR and Fixed Residue would have remained the same 
        # based on your research that they don't scale with net usage.
        return (gross_energy_cost + self.actual_cepr_cost + self.fixed_residue).quantize(Decimal("0.01"))

    def estimate_monthly_savings(self) -> Decimal:
        """
        The pure dollar value saved this month by solar production.
        """
        return self.calculate_shadow_cost() - self.bill.total_electric_due

    def calculate_new_bank_state(self, starting_bank: SolarBankState) -> SolarBankState:
        """
        Standard non-negative kWh banking logic.
        """
        net_on_peak = self.bill.delivered_by_customer.on_peak_kwh - self.bill.delivered_by_xcel.on_peak_kwh
        net_off_peak = self.bill.delivered_by_customer.off_peak_kwh - self.bill.delivered_by_xcel.off_peak_kwh
        
        new_on_peak = max(Decimal("0.00"), starting_bank.on_peak_kwh + net_on_peak)
        new_off_peak = max(Decimal("0.00"), starting_bank.off_peak_kwh + net_off_peak)
        
        return SolarBankState(on_peak_kwh=new_on_peak, off_peak_kwh=new_off_peak)
    
    def calculate_excess_value(self, excess_kwh: Decimal, rate: Decimal) -> Decimal:
        # Xcel also credits the variable riders (ECA, PCCA, etc.) 
        # Usually this is effectively the (Total Rate * Excess kWh)
        return excess_kwh * rate

    def calculate_billed_kwh(self, starting_bank: SolarBankState) -> EnergyUsage:
        """
        Calculates the kWh you are actually charged for after draining the bank.
        """
        # Usage that wasn't covered by current production
        net_needed_on = self.bill.delivered_by_xcel.on_peak_kwh - self.bill.delivered_by_customer.on_peak_kwh
        net_needed_off = self.bill.delivered_by_xcel.off_peak_kwh - self.bill.delivered_by_customer.off_peak_kwh
        
        # Subtract what we can from the bank
        billed_on = max(Decimal("0.00"), net_needed_on - starting_bank.on_peak_kwh)
        billed_off = max(Decimal("0.00"), net_needed_off - starting_bank.off_peak_kwh)
        
        return EnergyUsage(on_peak_kwh=billed_on, off_peak_kwh=billed_off)
    
    def _calculate_variable_costs(self, usage_on: Decimal, usage_off: Decimal) -> Decimal:
        """

                Helper to apply effective rates to kWh.

        NOT CURRENTLY USED - This is a placeholder for potential future logic to handle 
        more complex rate structures.

        TODO: Investigate CEPR FS kWh calculation. <-- Note, per recent research,
        CEPR FS kWh does not always match net usage. This suggests there may be 
        additional logic Xcel applies to determine CEPR FS charges, such as:
         - Proration based on mid-month rate changes.
         - Exclusion of specific 'baseline' kWh blocks.
         - Potential banding/capping logic.

        This helper would allow us to apply effective rates to the billed kWh 
        after accounting for any such logic, rather than relying on a simple 
        net usage * rate calculation.
        Note: Observed kWh for CEPR FS does not always equal Total Usage.
        Check for: 
        1. Proration based on mid-month rate changes.
        2. Exclusion of specific 'baseline' kWh blocks.
        3. Potential banding/capping logic.
        """
        #eff_on = self.RATE_ON_PEAK + self.RATE_CEPR_FS
        #eff_off = self.RATE_OFF_PEAK + self.RATE_CEPR_FS
        
        return (usage_on * eff_on) + (usage_off * eff_off)