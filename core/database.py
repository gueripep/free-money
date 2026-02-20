import sqlite3
import json
from typing import List, Dict, Optional
from core.config import DB_FILE, setup_logging

logger = setup_logging("database")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            isin TEXT PRIMARY KEY,
            ticker TEXT UNIQUE,
            name TEXT,
            market TEXT,
            compartment TEXT,
            market_cap REAL,
            float_shares REAL,
            revenue_growth REAL,
            profit_margins REAL,
            gross_margins REAL,
            operating_cash_flow REAL,
            annual_report_path TEXT,
            quarterly_report_path TEXT,
            recommendation TEXT,
            ten_x_potential INTEGER DEFAULT 0,
            rationale TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def update_stock_metrics(isin: str, metrics: Dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    for k, v in metrics.items():
        fields.append(f"{k} = ?")
        values.append(v)
        
    fields.append("last_updated = CURRENT_TIMESTAMP")
    values.append(isin)
    
    query = f"UPDATE stocks SET {', '.join(fields)} WHERE isin = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def get_launchpad_candidates(limit: int = 5) -> List[Dict]:
    """Find exponential return candidates based on strict metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT * FROM stocks 
        WHERE 
            market_cap BETWEEN 40000000 AND 1000000000
            AND float_shares < 25000000
            AND gross_margins > 0.6
            AND operating_cash_flow > 0
        ORDER BY 
            (revenue_growth + profit_margins) DESC
        LIMIT ?
    """
    cursor.execute(query, (limit,))
    stocks = [dict(row) for row in cursor.fetchall()]
    
    # Fallback if strict filter yields nothing
    if not stocks:
        logger.warning("Strict Launchpad filter yielded 0 results. Relaxing constraints for Discovery...")
        query = "SELECT * FROM stocks WHERE market_cap < 2000000000 ORDER BY revenue_growth DESC LIMIT ?"
        cursor.execute(query, (limit,))
        stocks = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    return stocks

def get_stock(ticker: str) -> Optional[Dict]:
    """Retrieves a single stock by its ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE ticker = ? OR isin = ?", (ticker, ticker))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_analysis(isin: str, analysis: Dict, lite_mode: bool = False):
    """Saves the AI verdict and rationale to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    rationale_text = f"SUMMARY: {analysis.get('verdict_summary', 'N/A')}\n\nDETAILS: {json.dumps(analysis.get('analysis', {}), indent=2)}"
    
    if lite_mode:
        cursor.execute('''
            UPDATE stocks 
            SET lite_recommendation = ?, lite_rationale = ?, last_updated = CURRENT_TIMESTAMP
            WHERE isin = ?
        ''', (
            analysis.get('recommendation', 'N/A'), 
            rationale_text, 
            isin
        ))
    else:
        cursor.execute('''
            UPDATE stocks 
            SET recommendation = ?, ten_x_potential = ?, rationale = ?, last_updated = CURRENT_TIMESTAMP
            WHERE isin = ?
        ''', (
            analysis.get('recommendation', 'N/A'), 
            1 if analysis.get('is_10_bagger_candidate', False) else 0, 
            rationale_text, 
            isin
        ))
        
    conn.commit()
    conn.close()

def update_manual_note(isin: str, note: str):
    """Updates the user's manual classification for a stock."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE stocks SET manual_note = ?, last_updated = CURRENT_TIMESTAMP WHERE isin = ?", (note, isin))
    conn.commit()
    conn.close()
