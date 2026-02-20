import os
import json
import time
import requests
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from core.config import EXCEL_FILE, TICKERS_JSON, setup_logging

logger = setup_logging("01_ingest_pea_pme")

def check_excel_exists() -> bool:
    """Checks if the user has manually downloaded the Excel file to data/"""
    if os.path.exists(EXCEL_FILE):
        return True
    
    # Try to find any excel file in the directory if the specific name isn't there
    data_dir = os.path.dirname(EXCEL_FILE)
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith('.xlsx'):
                logger.info(f"Found Excel file: {f}. Ensure it is named correctly in config or renamed.")
                return True
    return False

def resolve_isin_to_ticker(isin: str) -> Optional[str]:
    """Resolves an ISIN to a Yahoo Finance ticker symbol."""
    try:
        ticker = yf.Ticker(isin)
        return ticker.info.get('symbol')
    except Exception as e:
        logger.error(f"Error resolving {isin}: {e}")
        return None

def parse_stock_excel() -> List[Dict]:
    """Parses the Excel file and extracts stock metadata."""
    if not os.path.exists(EXCEL_FILE):
        logger.error(f"Excel file {EXCEL_FILE} not found. Ensure manual download or successful scrape.")
        return []

    try:
        initial_df = pd.read_excel(EXCEL_FILE, header=None).head(40)
        header_row_idx = 0
        for i, row in initial_df.iterrows():
            if any('isin' in str(cell).lower() for cell in row):
                header_row_idx = i
                break
        
        df = pd.read_excel(EXCEL_FILE, header=header_row_idx)
        
        col_map = {}
        target_keywords = {
            'isin': ['isin'],
            'name': ['société', 'company', 'name'],
            'market': ['march', 'market'],
            'compartment': ['compart']
        }

        for col in df.columns:
            low_col = str(col).lower()
            for key, keywords in target_keywords.items():
                if any(kw in low_col for kw in keywords):
                    col_map[key] = col

        stocks = []
        for _, row in df.iterrows():
            isin = str(row.get(col_map.get('isin', ''))).strip()
            if len(isin) == 12:
                stocks.append({
                    "isin": isin,
                    "name": str(row.get(col_map.get('name', 'Unknown'))).strip(),
                    "market": str(row.get(col_map.get('market', 'Unknown'))).strip(),
                    "compartment": str(row.get(col_map.get('compartment', 'Unknown'))).strip(),
                    "ticker": None
                })
        
        return stocks
    except Exception as e:
        logger.error(f"Excel parsing failed: {e}")
        return []

def run_ingestion():
    logger.info("Starting PEA-PME Ingestion Pipeline (Step 1)...")
    if not check_excel_exists():
        logger.error("No Excel file found in data/. Please download it manually from Euronext.")
        return
    
    stocks = parse_stock_excel()
    if not stocks:
        logger.error("No valid stocks found in input data.")
        return

    logger.info(f"Ingested {len(stocks)} stocks. Resolving sample tickers (limit 40)...")
    
    for i, stock in enumerate(stocks[:40]):
        ticker = resolve_isin_to_ticker(stock['isin'])
        if ticker:
            stock['ticker'] = ticker
        time.sleep(0.3)  # Gentle rate throttling

    with open(TICKERS_JSON, "w", encoding='utf-8') as f:
        json.dump(stocks, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Ingestion complete. Dataset saved to {TICKERS_JSON}")

if __name__ == "__main__":
    run_ingestion()
