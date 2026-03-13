import json
import time
import yfinance as yf
from typing import Dict, Optional, List
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import TICKERS_JSON, setup_logging, DATA_DIR
import core.database as db

LOCK_FILE = os.path.join(DATA_DIR, ".ingestion.lock")

logger = setup_logging("02_fetch_financials")

# Helper to get financial metrics

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None and not np.isnan(val) else default
    except (ValueError, TypeError):
        return default

def get_financial_metrics(ticker_name: str) -> Optional[Dict]:
    """Retrieves specific financial metrics for a given ticker."""
    try:
        ticker = ticker_name
        stock = yf.Ticker(ticker_name)
        info = stock.info

        # Initialize all metrics with "DATA NOT FOUND"
        metrics = {
            'market_cap': "DATA NOT FOUND",
            'revenue_growth': "DATA NOT FOUND",
            'profit_margins': "DATA NOT FOUND",
            'gross_margins': "DATA NOT FOUND",
            'operating_margins': "DATA NOT FOUND",
            'return_on_equity': "DATA NOT FOUND",
            'total_debt': "DATA NOT FOUND",
            'debt_to_equity': "DATA NOT FOUND",
            'free_cashflow': "DATA NOT FOUND",
            'enterprise_value': "DATA NOT FOUND",
            'ebitda': "DATA NOT FOUND",
            'operating_cash_flow': "DATA NOT FOUND",
            'float_shares': "DATA NOT FOUND",
            'roic_historical': "DATA NOT FOUND",
            'roic_decay_rate': "DATA NOT FOUND",
            'gross_margin_stability': "DATA NOT FOUND",
            'sga_efficiency_delta': "DATA NOT FOUND",
            'ebitda_margin_expansion': "DATA NOT FOUND",
            'roiic': "DATA NOT FOUND",
            'three_gp_score': "DATA NOT FOUND",
            'altman_z_score': "DATA NOT FOUND",
            'accruals_ratio': "DATA NOT FOUND",
            'cash_runway_months': "DATA NOT FOUND",
            'proxy_wacc': 0.10, # Default
            'inorganic_growth_ratio': 0.0,
            'is_acquirer': False,
            'shares_outstanding_cagr': 0.0 # Initialize
        }

        # Extracted metrics matching Launchpad criteria
        raw_keys = {
            'market_cap': 'marketCap',
            'revenue_growth': 'revenueGrowth',
            'profit_margins': 'profitMargins',
            'gross_margins': 'grossMargins',
            'operating_margins': 'operatingMargins',
            'return_on_equity': 'returnOnEquity',
            'total_debt': 'totalDebt',
            'debt_to_equity': 'debtToEquity',
            'free_cashflow': 'freeCashflow',
            'enterprise_value': 'enterpriseValue',
            'ebitda': 'ebitda',
            'operating_cash_flow': 'operatingCashflow',
            'float_shares': 'floatShares'
        }
        
        for m_key, info_key in raw_keys.items():
            val = info.get(info_key)
            if val is not None:
                metrics[m_key] = val
        
        # Calculate Advanced Calculus of Outperformance Metrics
        try:
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow
            income_stmt = stock.income_stmt
            
            # --- Historical Groos Margin Stability && SG&A Efficiency ---
            if 'Gross Profit' in financials.index and 'Total Revenue' in financials.index:
                gross_margins_hist = [
                    safe_float(gp) / safe_float(rev) 
                    for gp, rev in zip(financials.loc['Gross Profit'], financials.loc['Total Revenue']) 
                    if safe_float(rev) > 0
                ]
                if len(gross_margins_hist) > 1:
                    metrics['gross_margin_stability'] = float(np.std(gross_margins_hist))
            
            if 'Selling General And Administration' in financials.index and 'Total Revenue' in financials.index:
                sga_efficiency = [
                    safe_float(sga) / safe_float(rev) 
                    for sga, rev in zip(financials.loc['Selling General And Administration'], financials.loc['Total Revenue']) 
                    if safe_float(rev) > 0
                ]
                if len(sga_efficiency) >= 2:
                    # Positive delta means efficiency decreased (SG&A went up as % of rev), negative means it improved
                    metrics['sga_efficiency_delta'] = sga_efficiency[0] - sga_efficiency[-1] 

            # --- 3GP Score ---
            rev_growth = safe_float(metrics.get('revenue_growth'))
            ebitda_margin = safe_float(metrics.get('ebitda')) / safe_float(financials.loc['Total Revenue'].iloc[0]) if metrics.get('ebitda') and not financials.empty and 'Total Revenue' in financials.index and safe_float(financials.loc['Total Revenue'].iloc[0]) > 0 else 0
            if rev_growth is not None:
                metrics['three_gp_score'] = (3 * (rev_growth * 100)) + (ebitda_margin * 100)

            # --- EBITDA Margin Expansion ---
            if not financials.empty and 'Total Revenue' in financials.index:
                if 'EBITDA' in financials.index or 'Normalized EBITDA' in financials.index:
                    ebitda_key = 'EBITDA' if 'EBITDA' in financials.index else 'Normalized EBITDA'
                    ebitda_data = financials.loc[ebitda_key]
                    rev_data = financials.loc['Total Revenue']
                    margins = []
                    for e, r in zip(ebitda_data, rev_data):
                        e_val = safe_float(e)
                        r_val = safe_float(r)
                        if isinstance(e_val, (int, float)) and isinstance(r_val, (int, float)) and r_val > 0:
                            margins.append(e_val / r_val)
                    if len(margins) >= 2:
                        metrics['ebitda_margin_expansion'] = margins[0] - margins[-1]

            # --- Altman Z-Score ---
            if not balance_sheet.empty and not financials.empty:
                try:
                    current_assets = safe_float(balance_sheet.loc['Total Current Assets'].iloc[0]) if 'Total Current Assets' in balance_sheet.index else 0
                    current_liabilities = safe_float(balance_sheet.loc['Total Current Liabilities'].iloc[0]) if 'Total Current Liabilities' in balance_sheet.index else 0
                    total_assets = safe_float(balance_sheet.loc['Total Assets'].iloc[0]) if 'Total Assets' in balance_sheet.index else 1 # Avoid div by zero
                    retained_earnings = safe_float(balance_sheet.loc['Retained Earnings'].iloc[0]) if 'Retained Earnings' in balance_sheet.index else 0
                    ebit = safe_float(financials.loc['EBIT'].iloc[0]) if 'EBIT' in financials.index else 0
                    total_liabilities = safe_float(balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]) if 'Total Liabilities Net Minority Interest' in balance_sheet.index else 1
                    sales = safe_float(financials.loc['Total Revenue'].iloc[0]) if 'Total Revenue' in financials.index else 0
                    market_val_equity = safe_float(metrics.get('market_cap', 0))

                    working_capital = current_assets - current_liabilities
                    
                    z_score = (1.2 * (working_capital / total_assets)) + \
                              (1.4 * (retained_earnings / total_assets)) + \
                              (3.3 * (ebit / total_assets)) + \
                              (0.6 * (market_val_equity / total_liabilities)) + \
                              (1.0 * (sales / total_assets))
                              
                    metrics['altman_z_score'] = z_score
                except Exception as e:
                    logger.debug(f"Missing fields for Altman Z-Score for {ticker}: {e}")
            # --- Share Dilution Tracking (Roll-up Screener) ---
            shares_cagr = 0.0
            if not income_stmt.empty and 'Basic Average Shares' in income_stmt.index:
                shares_data = income_stmt.loc['Basic Average Shares'].dropna()
                if len(shares_data) >= 3:
                     curr_shares = safe_float(shares_data.iloc[0])
                     old_shares = safe_float(shares_data.iloc[2]) # 3 years ago
                     if old_shares > 0 and curr_shares > 0:
                         shares_cagr = (curr_shares / old_shares) ** (1/2) - 1
                elif len(shares_data) == 2:
                     curr_shares = safe_float(shares_data.iloc[0])
                     old_shares = safe_float(shares_data.iloc[1])
                     if old_shares > 0 and curr_shares > 0:
                         shares_cagr = (curr_shares / old_shares) - 1
            metrics['shares_outstanding_cagr'] = shares_cagr

            # --- Accruals Ratio ---
            if not cashflow.empty and not financials.empty and not balance_sheet.empty:
                net_income = safe_float(financials.loc['Net Income'].iloc[0]) if 'Net Income' in financials.index else 0
                ocf = safe_float(cashflow.loc['Operating Cash Flow'].iloc[0]) if 'Operating Cash Flow' in cashflow.index else 0
                total_assets = safe_float(balance_sheet.loc['Total Assets'].iloc[0]) if 'Total Assets' in balance_sheet.index else 1
                
                metrics['accruals_ratio'] = (net_income - ocf) / total_assets

            # --- Cash Runway Months ---
            if not cashflow.empty and not balance_sheet.empty:
                cash = safe_float(balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]) if 'Cash And Cash Equivalents' in balance_sheet.index else 0
                ocf = safe_float(cashflow.loc['Operating Cash Flow'].iloc[0]) if 'Operating Cash Flow' in cashflow.index else 0
                capex = safe_float(cashflow.loc['Capital Expenditure'].iloc[0]) if 'Capital Expenditure' in cashflow.index else 0
                
                burn_rate = ocf + capex # Usually capex is negative in CF statement
                if burn_rate < 0:
                    metrics['cash_runway_months'] = (cash / abs(burn_rate)) * 12
                else:
                    metrics['cash_runway_months'] = 999 # Technically infinite if generating cash

            # --- ROIC and ROIIC Metrics ---
            # Approximating Invested Capital = Total Assets - Current Liabilities + Short Term Debt (if any)
            ic_hist = []
            nopat_hist = []
            
            if not financials.empty and not balance_sheet.empty:
                cols = min(len(financials.columns), len(balance_sheet.columns))
                for i in range(cols):
                    ta = safe_float(balance_sheet.iloc[:, i].get('Total Assets', 0))
                    cl = safe_float(balance_sheet.iloc[:, i].get('Total Current Liabilities', 0))
                    ic = ta - cl
                    if ic == 0: continue
                    ic_hist.append(ic)
                    
                    ebit = safe_float(financials.iloc[:, i].get('EBIT', 0))
                    tax_provision = safe_float(financials.iloc[:, i].get('Tax Provision', 0))
                    pretax = safe_float(financials.iloc[:, i].get('Pretax Income', 0))
                    tax_rate = (tax_provision / pretax) if pretax > 0 else 0.21 # Default corporate rate fallback
                    nopat = ebit * (1 - tax_rate)
                    nopat_hist.append(nopat)
            
            if len(ic_hist) >= 2 and len(nopat_hist) >= 2:
                # ROIIC: (NOPAT t - NOPAT t-1) / (IC t-1 - IC t-2)
                if len(ic_hist) >= 3 and len(nopat_hist) >= 2:
                    delta_nopat = nopat_hist[0] - nopat_hist[1]
                    delta_ic = ic_hist[1] - ic_hist[2]
                    if delta_ic != 0:
                        metrics['roiic'] = delta_nopat / delta_ic
                
                # Historic ROIC
                roic_hist = [n / i for n, i in zip(nopat_hist, ic_hist) if i > 0]
                metrics['roic_historical'] = json.dumps(roic_hist)
                
                if len(roic_hist) >= 2:
                    metrics['roic_decay_rate'] = (roic_hist[0] - roic_hist[1]) / abs(roic_hist[1]) if roic_hist[1] != 0 else 0

            # --- Inorganic Growth Detection (M&A) ---
            inorganic_ratio = 0.0
            is_acquirer = False
            
            # Sub-check 1: Current Cash Flow Outflows (TTM)
            if not cashflow.empty:
                ocf = safe_float(cashflow.loc['Operating Cash Flow'].iloc[0]) if 'Operating Cash Flow' in cashflow.index else 0.0
                purchase_of_business = safe_float(cashflow.loc['Purchase Of Business'].iloc[0]) if 'Purchase Of Business' in cashflow.index else 0.0
                
                if ocf > 0:
                    if purchase_of_business < 0:
                        # Explicit Purchase Of Business line exists
                        inorganic_ratio_cf = abs(purchase_of_business) / ocf
                        inorganic_ratio += inorganic_ratio_cf
                    else:
                        # Fallback: Unexplained Investing Cash Flow
                        inv_cf = safe_float(cashflow.loc['Investing Cash Flow'].iloc[0]) if 'Investing Cash Flow' in cashflow.index else 0.0
                        capex = safe_float(cashflow.loc['Capital Expenditure'].iloc[0]) if 'Capital Expenditure' in cashflow.index else 0.0
                        if inv_cf < 0:
                            unexplained_investing = abs(inv_cf) - abs(capex)
                            if unexplained_investing > 0:
                                inorganic_ratio_cf = unexplained_investing / ocf
                                inorganic_ratio += inorganic_ratio_cf

            # Sub-check 2: YoY Goodwill/Intangibles Jump (Balance Sheet) -> Catches Base Effect & missing categorizations
            if not balance_sheet.empty:
                total_assets = safe_float(balance_sheet.loc['Total Assets'].iloc[0]) if 'Total Assets' in balance_sheet.index else 1.0
                
                # Waterfall through possible naming conventions
                gw_keys = ['Goodwill', 'Goodwill And Other Intangible Assets', 'Other Intangible Assets']
                for key in gw_keys:
                    if key in balance_sheet.index and len(balance_sheet.loc[key]) >= 2:
                        current_gw = safe_float(balance_sheet.loc[key].iloc[0])
                        prev_gw = safe_float(balance_sheet.loc[key].iloc[1])
                        if current_gw > prev_gw and current_gw > 0:
                            delta_gw = current_gw - prev_gw
                            inorganic_ratio_gw = delta_gw / total_assets
                            inorganic_ratio += inorganic_ratio_gw * 2  # Weight structural jumps heavily
                            break # Found a match, stop looking further down the waterfall
            
            metrics['inorganic_growth_ratio'] = inorganic_ratio
            if inorganic_ratio > 0.15: # 15% combined threshold
                metrics['is_acquirer'] = True
                
                # The "Roll-up Screener" Logic
                margin_trajectory = metrics.get('ebitda_margin_expansion', 0.0)
                shares_cagr = metrics.get('shares_outstanding_cagr', 0.0)
                
                # Debt to EBITDA (Handle negative or zero ebitda safely)
                ebitda = safe_float(metrics.get('ebitda', 0.0))
                total_debt = safe_float(metrics.get('total_debt', 0.0))
                if ebitda > 0:
                    debt_to_ebitda = total_debt / ebitda
                else:
                    debt_to_ebitda = 999.0 if total_debt > 0 else 0.0
                
                # We calculated debt_to_ebitda above, but won't save it to db since it is not in the schema.
                
                if shares_cagr > 0.03 or margin_trajectory < -0.02 or debt_to_ebitda > 4.0:
                    metrics['acquirer_type'] = "Dilutive" # Bad Acquirer: Issuing stock, margins diluting, or over-leveraged
                else:
                    metrics['acquirer_type'] = "Compounder" # Good Acquirer
            else:
                 metrics['acquirer_type'] = "None"

        except Exception as e:
            logger.warning(f"Could not calculate advanced metrics for {ticker}: {e}")

        # --- Dynamic WACC Proxy Calculation ---
        z_score = metrics.get('altman_z_score')
        if isinstance(z_score, (int, float)):
            if z_score > 3.0:
                metrics['proxy_wacc'] = 0.085 # Low risk
            elif z_score < 1.8:
                metrics['proxy_wacc'] = 0.15 # Higher risk premium
            else:
                metrics['proxy_wacc'] = 0.11 # Standard risk
        else:
            metrics['proxy_wacc'] = 0.10 # Default fallback if no Z-score

        # --- Upcoming Events Fetch ---
        try:
            cal = ticker_obj.calendar
            if not cal.empty:
                new_events = []
                for event_name, event_date in cal.items():
                    if pd.notnull(event_date):
                        new_events.append({"date": str(event_date.date()), "event": str(event_name)})
                if new_events:
                    metrics['upcoming_events'] = json.dumps(new_events)
        except Exception as e:
            logger.debug(f"Could not fetch calendar for {ticker}: {e}")

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

def run_batch_update(limit: int = None, progress_callback=None):
    """Updates missing Launchpad metrics in the database."""
    logger.info("Initializing PEA-PME database and populating base rows from JSON...")
    try:
        with open(TICKERS_JSON, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
            ingest_to_db(stocks)
    except FileNotFoundError:
        logger.error(f"{TICKERS_JSON} not found. Run 01_ingest_pea_pme.py first.")
        return

    logger.info("Fetching missing or stale Launchpad metrics (30 days) from Yahoo Finance...")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Select stocks that either have NULL metrics OR haven't been updated in 30 days
    query1 = '''
        SELECT isin, ticker, name, last_updated 
        FROM stocks 
        WHERE ticker IS NOT NULL 
          AND (
            float_shares IS NULL 
            OR market_cap IS NULL 
            OR enterprise_value IS NULL 
            OR last_updated < datetime('now', '-30 days')
          )
    '''
    query2 = "SELECT isin, ticker, name, last_updated FROM stocks WHERE ticker IS NULL"
    
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

    logger.info(f"Processing {len(to_update)} stocks sequentially...")
    
    total = len(to_update)
    
    for i, row in enumerate(to_update):
        isin, ticker = row['isin'], row['ticker']
        name = row['name']
        
        if progress_callback:
            progress_callback(i + 1, total)
            
        if not ticker:
            logger.info(f"Resolving ticker for ISIN: {isin} ({name})")
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
                continue 
                
        logger.info(f"[{i+1}/{total}] Processing: {ticker} ({name})")
        try:
            metrics = get_financial_metrics(ticker)
            if metrics:
                db.update_stock_metrics(isin, metrics)
                logger.info(f"Successfully updated {ticker}")
        except Exception as e:
            logger.error(f"Failed processing {ticker}: {e}")
            
        time.sleep(1.0) # Polite rate limit

if __name__ == "__main__":
    if os.path.exists(LOCK_FILE):
        # Check if the process is actually running (simple PID check)
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0) # Throws error if process is dead
            logger.error(f"Ingestion already running (PID: {pid}). Exiting.")
            sys.exit(0)
        except (ProcessLookupError, ValueError, FileNotFoundError, OSError):
            logger.warning("Stale lock file found. Overwriting.")
            pass

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
            
        import sys
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
        run_batch_update(limit=limit)
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
