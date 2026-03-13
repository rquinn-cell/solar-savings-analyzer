# Xcel Solar Savings Analyzer (CO RE-TOU)

A precision financial modeler for Xcel Energy Colorado customers on the RE-TOU (Residential Energy Time-of-Use) rate plan. This tool calculates the **actual** ROI of solar production by modeling "Shadow Bills" and tracking multi-bucket solar banks.

## Key Features
- **Shadow Billing:** Calculates exactly what you would have paid without solar, isolating fixed fees from variable energy costs.
- **Solar Bank Tracking:** Implements the dual-bucket (On-Peak/Off-Peak) net-metering logic used by Xcel.
- **Dynamic Rate Scraping:** Automatically extracts current TOU rates and CEPR FS adjustments directly from PDF statements.
- **Privacy First:** Includes a built-in PII scrubber to anonymize account details before data analysis.

## Usage
1. Place your Xcel PDFs in the `/bills` folder (git-ignored).
2. Run `python export_clean_data.py` to generate an anonymized dataset.
3. Run `python run_analyzer.py` to see your cumulative savings and bank status.