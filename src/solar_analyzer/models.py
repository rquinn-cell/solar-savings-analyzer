from dataclasses import dataclass, field
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
class SolarBankState:
    on_peak_kwh: Decimal = Decimal("0.00")
    off_peak_kwh: Decimal = Decimal("0.00")
    dollar_balance: Decimal = Decimal("0.00") # <--- New Field: Tracks the Rollover Bank Dollar Credit

    def __add__(self, other):
        return SolarBankState(
            on_peak_kwh=self.on_peak_kwh + other.on_peak_kwh,
            off_peak_kwh=self.off_peak_kwh + other.off_peak_kwh
        )

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
    rollover_bank_balance: Decimal = Decimal("0.00")
    total_electric_due: Decimal = Decimal("0.00")

    # scrape rates from the bill
    on_peak_rate: Decimal = Decimal("0.00")
    off_peak_rate: Decimal = Decimal("0.00")
    cepr_fs_rate: Decimal = Decimal("0.00")
    # get the cepr_fs_kwh usage
    cepr_fs_kwh: Decimal = Decimal("0.00")
    # New financial fields for the bank
    rollover_bank_balance: Decimal = Decimal("0.00") # The total $ balance reported on the bill    

    # We should also capture the specific credits from the bill if possible
    # to help the calculator stay in sync with Xcel's math

    @property
    def net_usage(self) -> EnergyUsage:
        """Calculates the Net values seen in the PDF."""
        return EnergyUsage(
            on_peak_kwh=self.delivered_by_xcel.on_peak_kwh - self.delivered_by_customer.on_peak_kwh,
            off_peak_kwh=self.delivered_by_xcel.off_peak_kwh - self.delivered_by_customer.off_peak_kwh
        )
    
    def to_scrubbed_dict(self):
        """Returns the bill data minus PII like Account Number."""
        return {
            "date": str(self.statement_date),
            "usage": {
                "on_peak": float(self.delivered_by_xcel.on_peak_kwh),
                "off_peak": float(self.delivered_by_xcel.off_peak_kwh)
            },
            "rates": {
                "on_peak": float(self.on_peak_rate),
                "off_peak": float(self.off_peak_rate)
            },
            "total_due": float(self.total_electric_due)
        }