from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class EnergyUsage:
    """Represents a specific bucket of energy from the RETOU table."""
    on_peak_kwh: Decimal
    off_peak_kwh: Decimal

    @property
    def total_kwh(self) -> Decimal:
        return self.on_peak_kwh + self.off_peak_kwh 
    

@dataclass
class XcelSolarBill:
    """The 'Near-Professional' representation of your monthly statement."""
    account_number: str  # PII: To be scrubbed in public version
    statement_date: date
    service_start: date
    service_end: date
    
    # Metered Data 
    delivered_by_xcel: EnergyUsage
    delivered_by_customer: EnergyUsage

    # Financials [cite: 106, 107]
    rollover_bank_balance: Decimal
    total_electric_due: Decimal

    @property
    def net_usage(self) -> EnergyUsage:
        """Calculates the Net values seen in the PDF."""
        return EnergyUsage(
            on_peak_kwh=self.delivered_by_xcel.on_peak_kwh - self.delivered_by_customer.on_peak_kwh,
            off_peak_kwh=self.delivered_by_xcel.off_peak_kwh - self.delivered_by_customer.off_peak_kwh
        )
    