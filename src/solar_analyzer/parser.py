import os
import re
import pdfplumber
from decimal import Decimal
from datetime import datetime
from src.solar_analyzer.models import XcelSolarBill, EnergyUsage

# Get the directory where THIS script is located
#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Join it with your filename
#PDF_PATH = os.path.join(BASE_DIR, "XcelBill-2026-01-02.pdf")

def extract_total_kwh(pattern, text):
    """
    Finds ALL occurrences of the pattern and returns the SUM.
    Handles the 'zero-day' anomaly by aggregating all readings.
    """
    matches = re.findall(pattern, text)
    if matches:
        # Convert all found strings to Decimals and sum them
        return sum(Decimal(m.replace(',', '')) for m in matches)
    return Decimal("0.0")

def parse_date(date_str):
    # Handles 11/23/25 -> 2025-11-23
    # We use %y (lowercase) for 2-digit years
    return datetime.strptime(date_str, "%m/%d/%y").date()

def parse_xcel_pdf(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not find file at {path}")

    with pdfplumber.open(path) as pdf:
        # --- Page 1: Metadata & Summary ---
        page_1_text = pdf.pages[0].extract_text()

        # 1. Statement Date (Format: 01/02/2026) and Due Date

        # This looks for the label, then allows for any characters (including quotes and newlines) 
        # until it hits a date pattern. re.DOTALL is the key here.
        stmt_match = re.search(r"STATEMENT\s*DATE\s*[^/]*?(\d{2}/\d{2}/\d{4})", page_1_text, re.IGNORECASE)
        statement_date = datetime.strptime(stmt_match.group(1), "%m/%d/%Y").date() if stmt_match else None

        due_match = re.search(r"DUE\s*DATE\s*[^/]*?(\d{2}/\d{2}/\d{4})", page_1_text, re.IGNORECASE)
        due_date = datetime.strptime(due_match.group(1), "%m/%d/%Y").date() if due_match else None

        # 2. Total Electric Due
        # Matches "ElectricityService" or "Electricity Service"
        # Handles "-$15.72 CR" or "$90.93"
        # Updated regex to be much more specific about the ending
        # It looks for: ElectricityService ... something ... then a number at the end
        elec_pat = r"Electricity\s*Service[\s\S]*?([-\$]?[\d\.,]+)\s*(CR)?\s*(?:\n|$)"
        elec_match = re.search(elec_pat, page_1_text)

        total_electric_due = Decimal("0.00")
        if elec_match:
            # 1. Clean the string
            raw_val = elec_match.group(1).replace('$', '').replace(',', '').strip()
            
            # 2. Handle the "2.0" bug: 
            # If the regex accidentally caught "2026" from a date, 
            # we need to ensure we are grabbing the actual currency.
            # Let's use findall and take the LAST match on that line to be safe.
            all_values = re.findall(r"([-\$]?\d{1,3}(?:[\.,]\d{2,3})+)\s*(CR)?", elec_match.group(0))
            if all_values:
                # Take the last one (the price)
                val_str, cr_label = all_values[-1]
                val_str = val_str.replace('$', '').replace(',', '')
                total_electric_due = Decimal(val_str)
                if cr_label == "CR":
                    total_electric_due = -abs(total_electric_due)

        # 3. Extract Account Number: 53-0012756531-8
        acc_match = re.search(r"(\d{2}-\d{10}-\d)", page_1_text)
        account_num = acc_match.group(1) if acc_match else "UNKNOWN"

        # 4. Extract Service Dates: 11/23/25-12/25/25
        # We look for the date range pattern
        dates_match = re.search(r"(\d{2}/\d{2}/\d{2})-(\d{2}/\d{2}/\d{2})", page_1_text)
        start_dt = parse_date(dates_match.group(1)) if dates_match else None
        end_dt = parse_date(dates_match.group(2)) if dates_match else None

        # 5a. Monthly Bank Contribution (The April Bill "No Decimal" Fix)
        # Matches "Other Recurring Charges" then looks for digits/spaces
        # this is actually matching the monthly contribution line
        bank_pat = r"Other\s*Recurring\s*Charges[\s\S]*?\$?\s*([\d\s\.,]{2,7})"
        bank_match = re.search(bank_pat, page_1_text)
        
        monthly_bank_contribution = Decimal("0.00")
        if bank_match:
            raw_val = bank_match.group(1).strip()
            # If we see "24 19" (space instead of dot), fix it
            if " " in raw_val and "." not in raw_val:
                raw_val = raw_val.replace(" ", ".")
            
            # Clean up commas and remaining spaces
            clean_val = raw_val.replace(',', '').replace(' ', '')
            if clean_val:
                monthly_bank_contribution = Decimal(clean_val)

        ## --- Page 2: Meter Data ---
        #page_2_text = pdf.pages[1].extract_text()
        # Aggregate text from relevant pages to handle overflows
        full_bill_text = ""
        for page in pdf.pages[1:4]: # Scan Pages 2 thru 4
            full_bill_text += page.extract_text()

        # Guardrail: Check for Legacy 3-Tier (RE-TOU) structure
        # if "MidPk" in full_bill_text:
        #     is_january_transition = (statement_date.year == 2026 and statement_date.month == 1)
        #     if not is_january_transition:
        #         raise ValueError(
        #             f"Legacy 3-tier bill detected for statement date {statement_date}. "
        #             "The current calculator only supports the 2-tier (On-Peak/Off-Peak) "
        #             "RE-TOU structure introduced in late 2025."
        #         )

        # 5b. Total Bank Balance (The April Bill "No Decimal" Fix)
        # Matches "Other Recurring Charges" then looks for digits/spaces
        # this is actually matching the monthly contribution line
        bank_pat = r"Rollover\s*Bank\s*Dollar\s*Credit[\s\S]*?\$?\s*([\d\s\.,]{2,7})"
        bank_match = re.search(bank_pat, full_bill_text)
        
        rollover_bank_balance = Decimal("0.00")
        if bank_match:
            raw_val = bank_match.group(1).strip()
            # If we see "24 19" (space instead of dot), fix it
            if " " in raw_val and "." not in raw_val:
                raw_val = raw_val.replace(" ", ".")
            
            # Clean up commas and remaining spaces
            clean_val = raw_val.replace(',', '').replace(' ', '')
            if clean_val:
                rollover_bank_balance = Decimal(clean_val)

        delivered_on = extract_total_kwh(r"On\s*Peak\s*Delivered\s*by\s*Xcel\s+(\d+)", full_bill_text)
        delivered_off = extract_total_kwh(r"Off\s*Peak\s*Delivered\s*by\s*Xcel\s+([\d,]+)", full_bill_text)
        
        received_on = extract_total_kwh(r"On\s*Pk\s*Delivered\s*by\s*Customer\s+(\d+)", full_bill_text)
        received_off = extract_total_kwh(r"Off\s*Pk\s*Delivered\s*by\s*Customer\s+([\d,]+)", full_bill_text)
        
        # Updated 2025 Legacy Bridge: Handling squashed PDF text
        # Matches "MidPkDeliveredbyXcel 28" or "MidPkDeliveredbyXcel: 28"
        mid_del_pat = r"MidPkDeliveredbyXcel\s*([\d\.,]+)"

        # Matches "MidPkDeliveredbyCustomer 34"
        mid_rec_pat = r"MidPkDeliveredbyCustomer\s*([\d\.,]+)"

        mid_del = extract_total_kwh(mid_del_pat, full_bill_text)
        mid_rec = extract_total_kwh(mid_rec_pat, full_bill_text)

        # Fold Mid-Peak Usage (Delivered) into On-Peak (Conservative Cost)
        final_on_peak_delivered = delivered_on + mid_del

        # Fold Mid-Peak Gen (Received) into Off-Peak (Conservative Credit)
        final_off_peak_received = received_off + mid_rec

        # --- Page 2-4: Refined Rate Extraction ---

        # 1. Initialize variables with Fallbacks 
        # (Using your known Jan rates as the defaults)
        on_rate = Decimal("0.183310")
        off_rate = Decimal("0.067920")
        cepr_rate = Decimal("0.012500")
        cepr_usage = Decimal("0.00")

        # 2. Perform Scraping
        # Pattern: Look for 'RETOU On-Peak', then energy, then '$' followed by rate
        on_match = re.search(r"RETOU\s*On-Peak\s*[\d,.]+\s*kWh\s*\$([\d.]+)", full_bill_text)
        if on_match:
            on_rate = Decimal(on_match.group(1))

        off_match = re.search(r"RETOU\s*Off-Peak\s*[\d,.]+\s*kWh\s*\$([\d.]+)", full_bill_text)
        if off_match:
            off_rate = Decimal(off_match.group(1))

        # CEPR FS captures both the specific usage and the rate
        cepr_match = re.search(r"CEPR\s*FS\s*([\d,.]+)\s*kWh\s*\$([\d.]+)", full_bill_text)
        if cepr_match:
            cepr_usage = Decimal(cepr_match.group(1))
            cepr_rate = Decimal(cepr_match.group(2))
        
        # Return the high-level object we defined in models.py
        return XcelSolarBill(
            account_number=account_num,
            statement_date=statement_date, 
            service_start=start_dt,
            service_end=end_dt,
            delivered_by_xcel=EnergyUsage(
                on_peak_kwh=final_on_peak_delivered, 
                off_peak_kwh=delivered_off
            ),
            delivered_by_customer=EnergyUsage(
                on_peak_kwh=received_on, 
                off_peak_kwh=final_off_peak_received
            ),
            on_peak_rate=on_rate,
            off_peak_rate=off_rate,
            cepr_fs_rate=cepr_rate,
            cepr_fs_kwh=cepr_usage,
            total_electric_due=total_electric_due,
            monthly_bank_contribution=monthly_bank_contribution,
            rollover_bank_balance=rollover_bank_balance
        )


# This is a simple function to peek at the PDF content.
""" def peek_at_bill(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"ERROR: Could not find file at {pdf_path}")
        return
        
    with pdfplumber.open(pdf_path) as pdf:
        # Page 2 contains the RETOU (Time of Use) breakdown
        page = pdf.pages[1] 
        text = page.extract_text()
        
        print(f"--- Raw Extraction from Page 2 ---\n")
        print(text)

if __name__ == "__main__":
    # Point this to your actual file path
    peek_at_bill(PDF_PATH)
 """