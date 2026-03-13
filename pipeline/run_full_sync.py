import os
import sys
import subprocess
import importlib.util
import time

# Define PROJECT_ROOT
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from core.config import setup_logging, DATA_DIR
logger = setup_logging("run_full_sync")

LOCK_FILE = os.path.join(DATA_DIR, ".ingestion.lock")

def main():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            logger.error("Sync already running. Exiting.")
            sys.exit(0)
        except (ProcessLookupError, ValueError, OSError):
            pass

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        logger.info("Starting Full Ingestion & Refresh...")
        
        # 1. Phase 1: Ingest
        spec = importlib.util.spec_from_file_location("ingest_stocks", os.path.join(PROJECT_ROOT, "pipeline", "01_ingest_stocks.py"))
        ingest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ingest)
        ingest.run_ingestion()
        
        # 2. Phase 2: Fetch Financials
        # We import and run to keep it in the same process (so PID matches lock)
        spec = importlib.util.spec_from_file_location("fetch_financials", os.path.join(PROJECT_ROOT, "pipeline", "02_fetch_financials.py"))
        fetch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fetch)
        fetch.run_batch_update()
        
        logger.info("Full Sync Complete.")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()
