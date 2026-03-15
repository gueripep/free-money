import os
import sys
import importlib.util
import time

# Define PROJECT_ROOT
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

import core.database as db
from core.config import setup_logging, DATA_DIR

logger = setup_logging("refresh_dashboard")
LOCK_FILE = os.path.join(DATA_DIR, ".ingestion.lock")

def run_refresh():
    """Refreshes metrics for all companies matching the dashboard/Launchpad criteria."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            logger.error(f"Another ingestion process is already running (PID: {pid}). Exiting.")
            return
        except (ProcessLookupError, ValueError, OSError):
            pass

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))

        logger.info("Starting Dashboard Candidates Refresh...")
        
        # Get all candidates currently in the dashboard
        candidates = db.get_all_candidates()
        
        if not candidates:
            logger.info("No dashboard candidates found to refresh.")
            return

        logger.info(f"Found {len(candidates)} candidates. Refreshing metrics from Yahoo Finance...")

        # Load fetcher module
        spec = importlib.util.spec_from_file_location("ff", os.path.join(PROJECT_ROOT, "pipeline", "02_fetch_financials.py"))
        ff = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ff)

        total = len(candidates)
        for i, stock in enumerate(candidates):
            ticker = stock['ticker']
            if not ticker:
                continue
                
            logger.info(f"[{i+1}/{total}] Refreshing {ticker} ({stock['name']})...")
            try:
                metrics = ff.get_financial_metrics(ticker)
                if metrics:
                    db.update_stock_metrics(stock['isin'], metrics)
                    logger.info(f"Successfully updated {ticker}")
            except Exception as e:
                logger.error(f"Failed to refresh {ticker}: {e}")
            
            # Polite rate limit to avoid IP bans from YF
            time.sleep(1.2)

        logger.info("Dashboard Refresh Complete.")

    except Exception as e:
        logger.error(f"Refresh failed: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    run_refresh()
