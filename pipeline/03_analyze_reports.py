import os
import sys
import datetime
import json
import yfinance as yf
from ai.gemini_client import GeminiClient
import core.database as db
from core.config import COMPANIES_DIR, DATA_DIR, setup_logging

logger = setup_logging("03_analyze_reports")

def generate_markdown_report(company_dir: str, ticker: str, stock: dict, analysis: dict, lite_mode: bool = False, custom_question: str = None):
    """Generates the Analysis.md (Deep Dive) or Analysis_Lite.md file."""
    filename = "Analysis_Lite.md" if lite_mode else "Analysis.md"
    md_path = os.path.join(company_dir, filename)
    
    with open(md_path, "w", encoding="utf-8") as f:
        title = "Lite Search Analysis" if lite_mode else "Rocket Fuel Deep Dive"
        f.write(f"# {title}: {stock['name']} ({ticker})\n\n")
        f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Source Document:** {stock.get('annual_report_path', 'Metrics Only') if not lite_mode else 'Google Search & Metrics'}\n")
        f.write(f"**Conviction Score:** {analysis.get('conviction_score', 'N/A')}/10\n")
        f.write(f"**10-Bagger Candidate:** {'YES' if analysis.get('is_10_bagger_candidate') else 'NO'}\n")
        f.write(f"**Verdict:** {analysis.get('recommendation', 'N/A')}\n\n")
        
        f.write("## Executive Summary\n")
        f.write(f"{analysis.get('verdict_summary', 'N/A')}\n\n")
        
        details = analysis.get('analysis', {})
        
        if lite_mode:
            f.write("## 1. Business Summary\n")
            f.write(f"{details.get('business_summary', 'N/A')}\n\n")
            
            f.write("## 2. Metrics Evaluation\n")
            f.write(f"{details.get('metrics_evaluation', 'N/A')}\n\n")
            
            f.write("## 3. Valuation Check\n")
            f.write(f"{details.get('valuation', 'N/A')}\n\n")
            
            f.write("## 4. Initial Gut Check\n")
            f.write(f"{details.get('initial_gut_check', 'N/A')}\n\n")
            
            f.write("## 5. Unknowns / Blank Spots\n")
            f.write(f"{details.get('unknowns', 'N/A')}\n\n")
        else:
            f.write("## 1. The Forensic Launchpad (Financials)\n")
            f.write(f"{details.get('forensic_launchpad', 'N/A')}\n\n")
            
            f.write("## 2. The Story (Lynch)\n")
            f.write(f"{details.get('the_story', 'N/A')}\n\n")
            
            f.write("## 3. The Gate (Phelps)\n")
            f.write(f"{details.get('the_gate', 'N/A')}\n\n")
            
            f.write("## 4. Rocket Fuel (O'Neil)\n")
            f.write(f"{details.get('rocket_fuel', 'N/A')}\n\n")
            
            f.write("## 5. Intelligent Fanatics (Cassel)\n")
            f.write(f"{details.get('intelligent_fanatics', 'N/A')}\n\n")
            
            f.write("## 6. The Valuation Check\n")
            f.write(f"{details.get('valuation', 'N/A')}\n\n")
            
            f.write("## 7. Red Flags\n")
            f.write(f"{details.get('red_flags', 'N/A')}\n\n")
            
            f.write("## 8. Pre-Mortem (The Bear Case)\n")
            f.write(f"{details.get('pre_mortem', 'N/A')}\n\n")
            
    logger.info(f"Updated {filename} in {company_dir}")

def process_target_stock(ticker: str, lite_mode: bool = False, custom_question: str = None):
    """Processes a single stock for deep dive or lite analysis."""
    stock = db.get_stock(ticker)
    
    if not stock:
        logger.error(f"Ticker {ticker} not found in database.")
        sys.exit(1)
        
    company_dir = os.path.join(COMPANIES_DIR, ticker)
    os.makedirs(company_dir, exist_ok=True)
    
    pdf_path = None
    doc_age_months = None
    if not lite_mode:
        # Look for PDF
        for file in os.listdir(company_dir):
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(company_dir, file)
                # Calculate document age
                mtime = os.path.getmtime(pdf_path)
                doc_date = datetime.datetime.fromtimestamp(mtime)
                delta = datetime.datetime.now() - doc_date
                doc_age_months = int(delta.days / 30.44)
                break
                
        if not pdf_path:
            logger.error(f"No PDF found in {company_dir}. Please upload the Annual Report.")
            return
            
        # Update DB with path
        db.update_stock_metrics(stock['isin'], {'annual_report_path': pdf_path})
        stock['annual_report_path'] = pdf_path # Update local dict
    
    mode_name = "LITE mode" if lite_mode else f"DEEP DIVE using {pdf_path}"
    logger.info(f"Running {mode_name} on {ticker}...")
    
    # Fetch Live Valuation Metrics
    try:
        logger.info(f"Fetching live valuation metrics from Yahoo Finance for {ticker}...")
        info = yf.Ticker(ticker).info
        stock['trailing_pe'] = info.get('trailingPE', 'N/A')
        stock['forward_pe'] = info.get('forwardPE', 'N/A')
        stock['price_to_book'] = info.get('priceToBook', 'N/A')
        stock['ev_to_ebitda'] = info.get('enterpriseToEbitda', 'N/A')
        stock['price_to_sales'] = info.get('priceToSalesTrailing12Months', 'N/A')
    except Exception as e:
        logger.error(f"Failed to fetch live valuation for {ticker}: {e}")
    
    # Fetch Lite Analysis Unknowns (if doing a Deep Dive)
    if not lite_mode:
        lite_path = os.path.join(company_dir, "Analysis_Lite.md")
        if os.path.exists(lite_path):
            logger.info("Existing Lite analysis found. Extracting Unknowns for Deep Dive context.")
            try:
                with open(lite_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "## 5. Unknowns / Blank Spots" in content:
                        unknowns_section = content.split("## 5. Unknowns / Blank Spots")[1].strip()
                        # Append to custom_question or create it
                        lite_context = f"\n\nIn a previous preliminary analysis, the following 'Unknowns / Blank Spots' were identified. Please specifically address these if the Annual Report provides the answers:\n{unknowns_section}"
                        custom_question = (custom_question or "") + lite_context
            except Exception as e:
                logger.error(f"Failed to extract Lite Unknowns for {ticker}: {e}")

    ai_client = GeminiClient()
    analysis = ai_client.analyze_stock(stock, lite_mode, custom_question, doc_age_months)
    
    if analysis:
        generate_markdown_report(company_dir, ticker, stock, analysis, lite_mode=lite_mode, custom_question=custom_question)
        db.save_analysis(stock['isin'], analysis, lite_mode=lite_mode)
        print(f"Success! Analysis complete for {ticker} ({mode_name}).")
    else:
        logger.error(f"Analysis failed for {ticker}")


def run_launchpad_batch(limit: int = 5):
    """Processes a batch of high-potential Launchpad candidates."""
    candidates = db.get_launchpad_candidates(limit)
    logger.info(f"Starting analysis for {len(candidates)} candidates.")
    
    ai_client = GeminiClient()
    for stock in candidates:
        ticker = stock.get('ticker') or stock['isin']
        logger.info(f"Analyzing {ticker}...")
        
        # In batch mode, if no reports exist, it runs just on metrics
        verdict = ai_client.analyze_stock(stock)
        if verdict:
            db.save_analysis(stock['isin'], verdict)
            logger.info(f"Verdict saved: {ticker} -> {verdict.get('recommendation')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_ticker = sys.argv[1]
        process_target_stock(target_ticker)
    else:
        run_launchpad_batch(limit=50)
