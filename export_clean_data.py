# export_clean_data.py
import sys
from pathlib import Path
from src.solar_analyzer.parser import parse_xcel_pdf
from src.solar_analyzer.scrubber import BillScrubber

def main():
    bills_dir = Path("bills")
    output_file = Path("data/bill_history_clean.json")
    
    if not bills_dir.exists():
        print("Error: 'bills/' directory not found. Place your PDFs there.")
        return

    clean_records = []
    
    # Process all PDFs in the ignored bills folder
    pdf_files = sorted(list(bills_dir.glob("*.pdf")))
    print(f"Found {len(pdf_files)} bills. Scrubbing...")

    for pdf_path in pdf_files:
        try:
            # Parse the private PDF
            bill = parse_xcel_pdf(str(pdf_path))
            
            # Scrub it
            clean_data = BillScrubber.scrub(bill)
            clean_records.append(clean_data)
            
            print(f"  [OK] {pdf_path.name}")
        except ValueError as e:
            print(f"  [SKIP] {pdf_path.name}: {e}")
        except Exception as e:
            print(f"  [ERROR] {pdf_path.name}: {e}")

    # Save to the public data file
    output_file.parent.mkdir(exist_ok=True)
    BillScrubber.save_history(clean_records, str(output_file))
    print(f"\nDone! Scrubbed data saved to {output_file}")
    print("You can now safely commit 'data/bill_history_clean.json' to GitHub.")

if __name__ == "__main__":
    main()
_