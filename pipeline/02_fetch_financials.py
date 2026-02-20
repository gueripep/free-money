import json
import time
import yfinance as yf
from typing import Dict, Optional, List
from core.config import TICKERS_JSON, setup_logging
import core.database as db

logger = setup_logging("02_fetch_financials")

def get_financial_metrics(ticker: str) -> Optional[Dict]:
    """Retrieves specific financial metrics for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Extracted metrics matching Launchpad criteria
        metrics = {
            'market_cap': info.get('marketCap'),
            'revenue_growth': info.get('revenueGrowth'),
            'profit_margins': info.get('profitMargins'),
            'gross_margins': info.get('grossMargins'),
            'operating_margins': info.get('operatingMargins'),
            'return_on_equity': info.get('returnOnEquity'),
            'total_debt': info.get('totalDebt'),
            'debt_to_equity': info.get('debtToEquity'),
            'free_cashflow': info.get('freeCashflow'),
            'enterprise_value': info.get('enterpriseValue'),
            'ebitda': info.get('ebitda'),
            'operating_cash_flow': info.get('operatingCashflow'),
            'float_shares': info.get('floatShares')
        }
        return metrics
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

def resolve_ticker(isin: str) -> Optional[str]:
    """Resolves an ISIN to a Yahoo Finance ticker."""
    try:
        ticker = yf.Ticker(isin)
        return ticker.info.get('symbol')
    except Exception:
        return None

def ingest_to_db(stocks: List[Dict]):
    """Ingests baseline stocks into the database from the JSON list."""
    db.init_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    for stock in stocks:
        cursor.execute('''
            INSERT OR IGNORE INTO stocks (isin, ticker, name, market, compartment)
            VALUES (?, ?, ?, ?, ?)
        ''', (stock['isin'], stock.get('ticker'), stock['name'], stock['market'], stock['compartment']))
    
    conn.commit()
    conn.close()

def run_batch_update(limit: int = None):
    """Updates missing Launchpad metrics in the database."""
    logger.info("Initializing PEA-PME database and populating base rows from JSON...")
    try:
        with open(TICKERS_JSON, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
            ingest_to_db(stocks)
    except FileNotFoundError:
        logger.error(f"{TICKERS_JSON} not found. Run 01_ingest_pea_pme.py first.")
        return

    logger.info("Fetching missing Launchpad metrics from Yahoo Finance...")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    query1 = '''
        SELECT isin, ticker FROM stocks 
        WHERE (float_shares IS NULL OR market_cap IS NULL OR enterprise_value IS NULL) AND ticker IS NOT NULL
    '''
    query2 = "SELECT isin, ticker FROM stocks WHERE ticker IS NULL"
    
    if limit:
        query1 += f" LIMIT {limit}"
        query2 += f" LIMIT {limit}"
        
    cursor.execute(query1)
    to_update = cursor.fetchall()
    
    cursor.execute(query2)
    to_update.extend(cursor.fetchall())

    conn.close()

    if not to_update:
        logger.info("No actionable missing data found.")
        return

    logger.info(f"Processing batch of {len(to_update)} stocks...")
    
    for row in to_update:
        isin, ticker = row['isin'], row['ticker']
        
        if not ticker:
            logger.info(f"Resolving ticker for ISIN: {isin}")
            ticker = resolve_ticker(isin)
            if ticker:
                db.update_stock_metrics(isin, {'ticker': ticker})
                
                # Update the json file map so we don't lose it if killed
                try:
                    with open(TICKERS_JSON, 'r', encoding='utf-8') as f:
                        all_stocks = json.load(f)
                    for s in all_stocks:
                        if s['isin'] == isin:
                            s['ticker'] = ticker
                            break
                    with open(TICKERS_JSON, 'w', encoding='utf-8') as f:
                        json.dump(all_stocks, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Failed to save ticker {ticker} to JSON: {e}")
                    
            else:
                logger.warning(f"Could not resolve ticker for ISIN: {isin}")
                # Mark as handled conceptually so we don't infinitely retry unless we add a flag, but for now we'll just continue
                continue 
                
        logger.info(f"Fetching metrics for: {ticker}")
        try:
            metrics = get_financial_metrics(ticker)
            if metrics:
                db.update_stock_metrics(isin, metrics)
        except Exception as e:
            logger.error(f"Failed processing {ticker}, likely rate limited.")
            
        time.sleep(1) # Rate limit yfinance requests

if __name__ == "__main__":
    run_batch_update(limit=None)
