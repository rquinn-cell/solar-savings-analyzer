from decimal import Decimal
from .models import XcelSolarBill, EnergyUsage, SolarBankState

class SolarSavingsCalculator:
    def __init__(self, bill: XcelSolarBill):
        self.bill = bill
        # Rates per January 2026 Bill
        self.RATE_ON_PEAK = Decimal("0.183310")
        self.RATE_OFF_PEAK = Decimal("0.067920")
        # compute a multiplier to account for rider adjustments and fixed costs
        on_pk = self.bill.net_usage.on_peak_kwh * self.RATE_ON_PEAK
        off_pk = self.bill.net_usage.off_peak_kwh * self.RATE_OFF_PEAK
        self.multiplier = ((self.bill.total_electric_due - Decimal("7.10")) / (on_pk + off_pk) 
                           if (on_pk + off_pk) > Decimal("0") else Decimal("1.0" ))
        # Note: These are simplified; real bills include multi-line 
        # adjustments (Wildfire, Transmission, etc.)
        # Multiplier above is a hack to account for those without parsing every line item.

    def return_multiplier(self) -> Decimal:
        """Returns the calculated multiplier for debugging purposes."""
        return self.multiplier
        
    def calculate_shadow_cost(self) -> Decimal:
        """Calculates cost of GROSS energy delivered by Xcel."""
        on_pk = self.bill.delivered_by_xcel.on_peak_kwh * self.RATE_ON_PEAK
        off_pk = self.bill.delivered_by_xcel.off_peak_kwh * self.RATE_OFF_PEAK
        return ((on_pk + off_pk) * self.multiplier).quantize(Decimal("0.01"))

    def estimate_monthly_savings(self, actual_electric_charges: Decimal) -> Decimal:
        """The difference between the Shadow Bill and what you actually paid."""
        return self.calculate_shadow_cost() - actual_electric_charges
    
    def calculate_new_bank_state(self, starting_bank: SolarBankState) -> SolarBankState:
        """
        Processes current bill against the bank. 
        Credits are added if production > usage.
        Credits are drained (down to 0.0) if usage > production.
        """
        # Calculate the net flow for this month
        # (Negative means we used more than we produced)
        net_on_peak = self.bill.delivered_by_customer.on_peak_kwh - self.bill.delivered_by_xcel.on_peak_kwh
        net_off_peak = self.bill.delivered_by_customer.off_peak_kwh - self.bill.delivered_by_xcel.off_peak_kwh
        
        # Apply to bank but ensure floor of 0.0
        new_on_peak = max(Decimal("0.00"), starting_bank.on_peak_kwh + net_on_peak)
        new_off_peak = max(Decimal("0.00"), starting_bank.off_peak_kwh + net_off_peak)
        
        return SolarBankState(on_peak_kwh=new_on_peak, off_peak_kwh=new_off_peak)

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

        NOT CURRENTLY USED - This is a placeholder for potential future logic to handle more complex rate structures.

        TODO: Investigate CEPR FS kWh calculation. 
        Note: Observed kWh for CEPR FS does not always equal Total Usage.
        Check for: 
        1. Proration based on mid-month rate changes.
        2. Exclusion of specific 'baseline' kWh blocks.
        3. Potential banding/capping logic.
        """
        eff_on = self.RATE_ON_PEAK + self.RATE_CEPR_FS
        eff_off = self.RATE_OFF_PEAK + self.RATE_CEPR_FS
        
        return (usage_on * eff_on) + (usage_off * eff_off)