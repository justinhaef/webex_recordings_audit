import os
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
# from dotenv import load_dotenv

# Internal Module Imports
from src.webex import WebexAuditClient


def main():
    # load_dotenv()
    
    parser = argparse.ArgumentParser(description="Webex Monthly Recording Audit")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    # 1. Initialize API Client
    webex = WebexAuditClient()
    

    # 2. Monthly Iteration Loop
    print(f"--- Phase 2: Starting Webex Audit for {args.start} ---")
    start_date = datetime.strptime(args.start, "%m/%d/%Y")
    end_date = datetime.strptime(args.end, "%m/%d/%Y")
    


    print(f"\nProcessing from {start_date}...")
        
    # A. Fetch Webex Recording Metadata for the month
    # This is where the Admin API work happens
    # Write the data CSV for this specific month
    webex_report_path = f"reports/missing_recordings/missing_{start_date.strftime('%Y_%m')}.csv"
    webex_data = webex.fetch_recordings_for_audit(start_date, end_date, webex_report_path)


    if not webex_data:
        print(f"No Webex records found for {start_date}.")


    print(f"--- {start_date} Audit Complete ---")
    print(f"CSV report saved to: {webex_report_path}")

if __name__ == "__main__":
    main()