import os
import json
import time
import pandas as pd
import yfinance as yf
from typing import Dict, Optional, List
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import UPLOAD_CSV, TICKERS_JSON, setup_logging
import core.database as db

logger = setup_logging("01_ingest_stocks")

def resolve_ticker_to_isin(ticker_symbol: str) -> Optional[str]:
    """Resolves a ticker symbol to its ISIN if possible."""
    try:
        t = yf.Ticker(ticker_symbol)
        # Some tickers have ISIN in their info
        isin = t.info.get('isin')
        return isin
    except Exception as e:
        logger.debug(f"Could not resolve ISIN for {ticker_symbol}: {e}")
        return None

def parse_stock_csv() -> List[Dict]:
    """Parses the uploaded CSV file."""
    if not os.path.exists(UPLOAD_CSV):
        logger.error(f"CSV file {UPLOAD_CSV} not found.")
        return []

    try:
        # Try to read with different delimiters
        try:
            df = pd.read_csv(UPLOAD_CSV)
        except:
            df = pd.read_csv(UPLOAD_CSV, sep=';')
            
        # Normalize columns
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        col_map = {}
        target_keywords = {
            'ticker': ['ticker', 'symbol', 'symbole', 'valeur'],
            'isin': ['isin'],
            'name': ['name', 'nom', 'société', 'company']
        }

        for col in df.columns:
            for key, keywords in target_keywords.items():
                if any(kw in col for kw in keywords):
                    col_map[key] = col
                    break

        if 'ticker' not in col_map and 'isin' not in col_map:
            logger.error("CSV must contain at least a 'Ticker' or 'ISIN' column.")
            return []

        stocks = []
        for _, row in df.iterrows():
            ticker = str(row.get(col_map.get('ticker', ''))).strip() if 'ticker' in col_map else None
            isin = str(row.get(col_map.get('isin', ''))).strip() if 'isin' in col_map else None
            name = str(row.get(col_map.get('name', ''))).strip() if 'name' in col_map else "Unknown"
            
            if ticker == 'nan': ticker = None
            if isin == 'nan': isin = None
            
            if not ticker and not isin:
                continue
                
            stocks.append({
                "ticker": ticker,
                "isin": isin,
                "name": name,
                "market": "Generic",
                "compartment": "Unknown"
            })
        
        return stocks
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        return []

def run_ingestion(progress_callback=None):
    logger.info("Starting Generic Stock Ingestion Pipeline...")
    stocks = parse_stock_csv()
    if not stocks:
        logger.error("No valid stocks found in input data.")
        return

    logger.info(f"Ingested {len(stocks)} stocks. Dataset saved to {TICKERS_JSON}")
    
    for stock in stocks:
        # Ensure we have a PK (ISIN). If missing, use Ticker as proxy.
        if not stock['isin'] and stock['ticker']:
            stock['isin'] = f"TICKER:{stock['ticker']}"
    
    with open(TICKERS_JSON, "w", encoding='utf-8') as f:
        json.dump(stocks, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Ingestion complete. Dataset saved to {TICKERS_JSON}")

if __name__ == "__main__":
    run_ingestion()
