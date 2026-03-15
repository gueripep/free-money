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
            operating_margins REAL,
            return_on_equity REAL,
            total_debt REAL,
            debt_to_equity REAL,
            free_cashflow REAL,
            enterprise_value REAL,
            ebitda REAL,
            operating_cash_flow REAL,
            annual_report_path TEXT,
            quarterly_report_path TEXT,
            recommendation TEXT,
            ten_x_potential INTEGER DEFAULT 0,
            rationale TEXT,
            lite_recommendation TEXT,
            lite_rationale TEXT,
            manual_note TEXT,
            roic_historical TEXT,
            roic_decay_rate REAL,
            gross_margin_stability REAL,
            sga_efficiency_delta REAL,
            ebitda_margin_expansion REAL,
            roiic REAL,
            three_gp_score REAL,
            altman_z_score REAL,
            accruals_ratio REAL,
            cash_runway_months REAL,
            proxy_wacc REAL,
            upcoming_events TEXT,
            composite_score REAL,
            mathematical_tier TEXT,
            organic_revenue_growth REAL,
            inorganic_growth_ratio REAL,
            is_acquirer BOOLEAN,
            shares_outstanding_cagr REAL,
            acquirer_type TEXT,
            tier TEXT,
            review_date TEXT,
            currency TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Simple migration logic for existing databases
    existing_columns = [col[1] for col in cursor.execute("PRAGMA table_info(stocks)").fetchall()]
    new_columns = [
        ("lite_recommendation", "TEXT"),
        ("lite_rationale", "TEXT"),
        ("manual_note", "TEXT"),
        ("roic_historical", "TEXT"),
        ("roic_decay_rate", "REAL"),
        ("gross_margin_stability", "REAL"),
        ("sga_efficiency_delta", "REAL"),
        ("ebitda_margin_expansion", "REAL"),
        ("roiic", "REAL"),
        ("three_gp_score", "REAL"),
        ("altman_z_score", "REAL"),
        ("accruals_ratio", "REAL"),
        ("cash_runway_months", "REAL"),
        ("proxy_wacc", "REAL"),
        ("upcoming_events", "TEXT"),
        ("composite_score", "REAL"),
        ("mathematical_tier", "TEXT"),
        ("organic_revenue_growth", "REAL"),
        ("inorganic_growth_ratio", "REAL"),
        ("is_acquirer", "BOOLEAN"),
        ("shares_outstanding_cagr", "REAL"),
        ("acquirer_type", "TEXT"),
        ("tier", "TEXT"),
        ("review_date", "TEXT"),
        ("currency", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE stocks ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass # Column exists or other error
                
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

def get_all_candidates() -> List[Dict]:
    """Fetches all stocks that have passed the initial screen and have metrics populated."""
    conn = get_connection()
    cursor = conn.cursor()
    # We want stocks that have at least one significant metric populated
    # and fit our basic micro-cap criteria
    query = """
        SELECT * FROM stocks 
        WHERE 
            market_cap BETWEEN 40000000 AND 1000000000
            AND float_shares < 25000000
            AND gross_margins > 0.6
            AND operating_cash_flow > 0
            AND revenue_growth IS NOT NULL
            AND (manual_note IS NULL OR manual_note != '🔴 Bad')
    """
    cursor.execute(query)
    stocks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stocks

def update_ranking_data(isin: str, score: float, tier: str):
    """Persists the mathematical ranking results to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE stocks 
        SET composite_score = ?, mathematical_tier = ?, last_updated = CURRENT_TIMESTAMP
        WHERE isin = ?
    ''', (score, tier, isin))
    conn.commit()
    conn.close()

def get_good_companies() -> List[Dict]:
    """Fetches all companies that have been manually marked as '🟢 Good'."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM stocks WHERE manual_note = '🟢 Good'"
    cursor.execute(query)
    stocks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stocks
