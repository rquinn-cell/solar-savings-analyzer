
import os
import re
import pdfplumber
from decimal import Decimal
from models import XcelSolarBill, EnergyUsage

# Get the directory where THIS script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Join it with your filename
PDF_PATH = os.path.join(BASE_DIR, "XcelBill-2026-01-02.pdf")

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

def parse_xcel_pdf(path):
    with pdfplumber.open(path) as pdf:
        if not os.path.exists(path):
            print(f"ERROR: Could not find file at {path}")
            return

        # Xcel bills can sometimes split info across pages, 
        # but the RETOU table is almost always Page 2.
        page_text = pdf.pages[1].extract_text()
        
        # We use re.MULTILINE if the PDF extraction puts values on new lines
        # The (\d+) captures the numeric value
        delivered_on = extract_total_kwh(r"On Pk Net Delivered by Xcel\s+(\d+)", page_text)
        delivered_off = extract_total_kwh(r"Off Pk Net Delivered by Xcel\s+([\d,]+)", page_text)
        
        received_on = extract_total_kwh(r"On Pk Net Received from Customer\s+(\d+)", page_text)
        received_off = extract_total_kwh(r"Off Pk Net Received from Customer\s+([\d,]+)", page_text)
        
        return delivered_on, delivered_off, received_on, received_off


#old parsing logic
"""         # Page 2 contains the meter details
        page_text = pdf.pages[1].extract_text()
        
        # Pattern: Look for the label, skip whitespace/labels, grab the number
        # Example: 'On Pk Net Delivered by Xcel 86'
        on_peak_delivered = extract_kwh(r"On Pk Net Delivered by Xcel\s+(\d+)", page_text)
        off_peak_delivered = extract_kwh(r"Off Pk Net Delivered by Xcel\s+([\d,]+)", page_text)
        
        # Customer Delivered (Solar Export)
        on_peak_received = extract_kwh(r"On Pk Net Received from Customer\s+(\d+)", page_text)
        off_peak_received = extract_kwh(r"Off Pk Net Received from Customer\s+([\d,]+)", page_text)
        
        return EnergyUsage(on_peak_kwh=on_peak_delivered, off_peak_kwh=off_peak_delivered), \
               EnergyUsage(on_peak_kwh=on_peak_received, off_peak_kwh=off_peak_received)
 """
if __name__ == "__main__":
    path = PDF_PATH
    on_d, off_d, on_r, off_r = parse_xcel_pdf(path)
    print(f"Results for {path}:")
    print(f"Delivered: {on_d} / {off_d}")
    print(f"Received:  {on_r} / {off_r}")    

"""     # Test it against your file
    delivered, received = parse_xcel_pdf(PDF_PATH)
    print(f"Xcel Delivered: {delivered.on_peak_kwh} On / {delivered.off_peak_kwh} Off")
    print(f"Solar Received: {received.on_peak_kwh} On / {received.off_peak_kwh} Off")
 """

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