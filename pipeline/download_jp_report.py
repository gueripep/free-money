import sys
import os

# Path fix for package imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import argparse
from core.edinet import EdinetClient
from core.config import DATA_DIR, setup_logging

logger = setup_logging("download_jp_report")

def main():
    parser = argparse.ArgumentParser(description="Download Japanese Annual or Quarterly/Interim Reports from EDINET.")
    parser.add_argument("ticker", help="Ticker symbol (e.g., 7203.T or 7203)")
    parser.add_argument("--days", type=int, default=400, help="Max lookback days for searching (default: 400)")
    parser.add_argument("--type", choices=["annual", "quarterly"], default="annual", help="Type of report to download (default: annual)")
    args = parser.parse_args()

    ticker = args.ticker
    if not ticker.endswith(".T") and len(ticker) == 4 and ticker.isdigit():
        ticker = f"{ticker}.T"

    client = EdinetClient()
    
    # 1. Find latest report
    if args.type == "annual":
        logger.info(f"Looking for latest Yuho (Annual) for {ticker}...")
        report = client.find_latest_yuho(ticker, max_lookback_days=args.days)
    else:
        logger.info(f"Looking for latest Quarterly/Interim for {ticker}...")
        # Search for Quarterly (043000), Interim (050000), and Semi-annual (043A00)
        report = client.find_latest_report(ticker, ["043000", "050000", "043A00"], max_lookback_days=args.days)
    
    if not report:
        logger.error(f"Could not find a recent {args.type} report for {ticker} within {args.days} days.")
        sys.exit(1)
        
    doc_id = report["doc_id"]
    file_date = report["date"]
    title = report["title"]
    
    logger.info(f"Found {args.type} report: {title} (ID: {doc_id}, Date: {file_date})")
    
    # 2. Download
    company_dir = os.path.join(DATA_DIR, "companies", ticker)
    os.makedirs(company_dir, exist_ok=True)
    
    if args.type == "annual":
        save_path = os.path.join(company_dir, f"yuho_{file_date}.pdf")
    else:
        # We use 'Interim_' prefix so the UI/Pipeline automatically picks it up
        # Sanitize title for filename
        clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_')]).strip()
        save_path = os.path.join(company_dir, f"Interim_{clean_title}_{file_date}.pdf")
    
    logger.info(f"Downloading to {save_path}...")
    if client.download_document(doc_id, save_path):
        logger.info("Successfully downloaded.")
        
        # For annual reports, we maintain the 'latest_report.pdf' convention
        if args.type == "annual":
            latest_path = os.path.join(company_dir, "latest_report.pdf")
            if os.path.exists(latest_path):
                os.remove(latest_path)
            try:
                os.link(save_path, latest_path) # Hard link
            except:
                import shutil
                shutil.copy2(save_path, latest_path)
        
        print(f"SUCCESS: Downloaded {ticker} {args.type} report to {save_path}")
    else:
        logger.error("Download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
