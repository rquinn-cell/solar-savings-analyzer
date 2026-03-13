# src/solar_analyzer/scrubber.py
import json
from pathlib import Path
from typing import List
from .models import XcelSolarBill

class BillScrubber:
    """
    Removes Personally Identifiable Information (PII) from bill data.
    Ensures Account Numbers and Addresses are never saved to disk.
    """
    
    @staticmethod
    def scrub(bill: XcelSolarBill) -> dict:
        return {
            "statement_date": str(bill.statement_date),
            "service_period": {
                "start": str(bill.service_start),
                "end": str(bill.service_end)
            },
            "usage_delivered": {
                "on_peak": float(bill.delivered_by_xcel.on_peak_kwh),
                "off_peak": float(bill.delivered_by_xcel.off_peak_kwh)
            },
            "usage_received": {
                "on_peak": float(bill.delivered_by_customer.on_peak_kwh),
                "off_peak": float(bill.delivered_by_customer.off_peak_kwh)
            },
            "rates": {
                "on_peak": float(bill.on_peak_rate),
                "off_peak": float(bill.off_peak_rate),
                "cepr_fs": float(bill.cepr_fs_rate)
            },
            "cepr_usage": float(bill.cepr_fs_kwh),
            "financials": {
                "total_due": float(bill.total_electric_due)
            }
        }

    @staticmethod
    def save_history(scrubbed_bills: List[dict], filepath: str = "data/bill_history_clean.json"):
        Path("data").mkdir(exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(scrubbed_bills, f, indent=4)
