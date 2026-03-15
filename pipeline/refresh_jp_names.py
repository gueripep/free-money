import os
import sys
import json
import sqlite3
from core.database import get_connection, update_stock_metrics
from core.config import DATA_DIR, setup_logging

logger = setup_logging("refresh_jp_names")

EDINET_MAPPING_FILE = os.path.join(DATA_DIR, "edinet_mapping.json")

def main():
    if not os.path.exists(EDINET_MAPPING_FILE):
        logger.error(f"EDINET mapping file not found at {EDINET_MAPPING_FILE}. Run a download first.")
        return

    with open(EDINET_MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    conn = get_connection()
    cursor = conn.cursor()
    
    # Find all Japanese companies in the database
    cursor.execute("SELECT isin, ticker, name FROM stocks WHERE ticker LIKE '%.T'")
    stocks = cursor.fetchall()
    
    updated_count = 0
    for stock in stocks:
        isin = stock['isin']
        ticker = stock['ticker']
        current_name = stock['name']
        
        # Clean ticker to match mapping key (4 digits)
        clean_ticker = ticker.split('.')[0]
        
        if clean_ticker in mapping:
            official_name = mapping[clean_ticker].get('name')
            if official_name and official_name != current_name:
                logger.info(f"Updating {ticker}: {current_name} -> {official_name}")
                update_stock_metrics(isin, {'name': official_name})
                updated_count += 1
    
    conn.close()
    print(f"SUCCESS: Updated names for {updated_count} Japanese companies.")

if __name__ == "__main__":
    main()
