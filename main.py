import os
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Internal Module Imports
from src.calabrio import load_calabrio_truth_set
from src.webex import WebexAuditClient
from src.reconciler import reconcile_batch
from src.database import AuditDatabase

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Webex-Calabrio Yearly Recording Audit")
    parser.add_argument("--csv", required=True, help="Path to the 6M-line Calabrio CSV")
    parser.add_argument("--start_year", type=int, default=2025, help="Year to audit")
    args = parser.parse_args()

    # 1. Initialize Database & API Client
    db = AuditDatabase("data/audit.db")
    webex = WebexAuditClient()
    
    # 2. Load the "Global Truth" Set (One-time memory hit)
    # This takes about 30-60 seconds for 6M records
    print(f"--- Phase 1: Ingesting Calabrio Master Data ---")
    calabrio_set = load_calabrio_truth_set(args.csv)
    print(f"Success. Loaded {len(calabrio_set):,} unique Recording IDs into memory.\n")

    # 3. Monthly Iteration Loop
    print(f"--- Phase 2: Starting Webex Audit for {args.start_year} ---")
    start_date = datetime(args.start_year, 1, 1)
    
    for i in range(12):
        month_start = start_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1) - relativedelta(seconds=1)
        month_str = month_start.strftime("%B %Y")

        # Check if month is already processed in DB
        if db.is_month_complete(month_str):
            print(f"[{month_str}] Already audited. Skipping...")
            continue

        print(f"\nProcessing {month_str}...")
        
        # A. Fetch Webex Recording Metadata for the month
        # This is where the Admin API work happens
        month_data = webex.fetch_recordings_for_audit(month_start, month_end)


        if not month_data:
            print(f"No Webex records found for {month_str}.")
            continue

        # B. The Lightning Diff (Set Intersection)
        match_rate, missing_calls = reconcile_batch(month_data, calabrio_set)

        # C. Save Results
        # Write the 'Missing' CSV for this specific month
        gap_report_path = f"reports/missing_recordings/missing_{month_start.strftime('%Y_%m')}.csv"
        db.save_monthly_results(
            month=month_str,
            total_count=len(month_data),
            match_rate=match_rate,
            missing_list=missing_calls,
            report_path=gap_report_path
        )

        print(f"--- {month_str} Audit Complete ---")
        print(f"Match Rate: {match_rate:.2f}%")
        print(f"Missing Calls: {len(missing_calls):,}")
        print(f"Detailed gap report saved to: {gap_report_path}")

    print("\n--- Yearly Audit Fully Complete ---")
    print("Final summary available in data/audit.db")

if __name__ == "__main__":
    main()