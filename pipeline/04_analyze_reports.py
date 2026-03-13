import os
import sys
import datetime
import json
import tempfile
import shutil
import yfinance as yf
from typing import Optional, List, Dict
from ai.gemini_client import GeminiClient
from ai.agents import TableExtractionAgent, NarrativeForensicAgent, SynthesisAgent
from ai.critic import CriticValidator
import core.database as db
from core.config import COMPANIES_DIR, DATA_DIR, setup_logging

logger = setup_logging("03_analyze_reports")

def generate_markdown_report(company_dir: str, ticker: str, stock: dict, analysis: dict, lite_mode: bool = False, custom_question: str = None, quarterly_mode: bool = False, quarterly_pdf_path: str = None):
    """Generates the Analysis.md (Deep Dive) or Analysis_Lite.md file."""
    if quarterly_mode and quarterly_pdf_path:
        basename = os.path.basename(quarterly_pdf_path)
        filename = f"Analysis_{basename}.md"
    else:
        filename = "Analysis_Lite.md" if lite_mode else "Analysis.md"
    
    md_path = os.path.join(company_dir, filename)
    
    with open(md_path, "w", encoding="utf-8") as f:
        if quarterly_mode:
            title = "Quarterly Sell Signal Update"
            source = basename
        else:
            title = "Lite Search Analysis" if lite_mode else "Rocket Fuel Deep Dive"
            source = stock.get('annual_report_path', 'Metrics Only') if not lite_mode else 'Google Search & Metrics'
            
        f.write(f"# {title}: {stock['name']} ({ticker})\n\n")
        f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Source Document:** {source}\n")
        
        if quarterly_mode:
            f.write(f"**Thesis Holds:** {'YES' if analysis.get('thesis_holds') else 'NO'}\n")
            f.write(f"**Recommendation:** {analysis.get('recommendation', 'N/A')}\n\n")
        else:
            f.write(f"**Conviction Score:** {analysis.get('conviction_score', 'N/A')}/10\n")
            f.write(f"**10-Bagger Candidate:** {'YES' if analysis.get('is_10_bagger_candidate') else 'NO'}\n")
            f.write(f"**Verdict:** {analysis.get('recommendation', 'N/A')}\n\n")
        
        f.write("## Executive Summary\n")
        f.write(f"{analysis.get('verdict_summary', 'N/A')}\n\n")
        
        f.write("## 1. Global Synthesis & Business Reality\n")
        f.write(f"{analysis.get('global_thought', 'N/A')}\n\n")
        
        details = analysis.get('analysis', {})
        
        if quarterly_mode:
            f.write("## 2. Thesis Tracking\n")
            f.write(f"{details.get('thesis_tracking', 'N/A')}\n\n")
            f.write("## 3. Financial Update\n")
            f.write(f"{details.get('financial_update', 'N/A')}\n\n")
            f.write("## 4. Red Flags\n")
            f.write(f"{details.get('red_flags', 'N/A')}\n\n")
            f.write("## 5. Management Tone\n")
            f.write(f"{details.get('management_tone', 'N/A')}\n\n")
            f.write("## 6. Valuation Check\n")
            f.write(f"{details.get('valuation_check', 'N/A')}\n\n")
        elif lite_mode:
            f.write("## 2. Business Summary\n")
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
            f.write("## 2. The Forensic Launchpad (Financials)\n")
            f.write(f"{details.get('forensic_launchpad', 'N/A')}\n\n")
            
            f.write("## 3. The Story (Lynch)\n")
            f.write(f"{details.get('the_story', 'N/A')}\n\n")
            
            f.write("## 4. The Gate (Phelps)\n")
            f.write(f"{details.get('the_gate', 'N/A')}\n\n")
            
            f.write("## 5. Rocket Fuel (O'Neil)\n")
            f.write(f"{details.get('rocket_fuel', 'N/A')}\n\n")
            
            f.write("## 6. Intelligent Fanatics (Cassel)\n")
            f.write(f"{details.get('intelligent_fanatics', 'N/A')}\n\n")
            
            f.write("## 7. The Valuation Check\n")
            f.write(f"{details.get('valuation', 'N/A')}\n\n")
            
            f.write("## 8. Red Flags\n")
            f.write(f"{details.get('red_flags', 'N/A')}\n\n")
            
            f.write("## 9. Pre-Mortem (The Bear Case)\n")
            f.write(f"{details.get('pre_mortem', 'N/A')}\n\n")
            
    logger.info(f"Updated {filename} in {company_dir}")

def process_target_stock(ticker: str, lite_mode: bool = False, custom_question: str = None, quarterly_mode: bool = False, quarterly_pdf_path: str = None, gemini_client: Optional[GeminiClient] = None):
    """Processes a single stock for deep dive or lite analysis."""
    stock = db.get_stock(ticker)
    
    if not stock:
        logger.error(f"Ticker {ticker} not found in database.")
        sys.exit(1)
        
    company_dir = os.path.join(COMPANIES_DIR, ticker)
    os.makedirs(company_dir, exist_ok=True)
    
    pdf_path = None
    doc_age_months = None
    if not lite_mode and not quarterly_mode:
        # Look for PDF
        for file in os.listdir(company_dir):
            if file.lower().endswith('.pdf') and not file.startswith('Interim_'):
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
    
    if quarterly_mode:
        mode_name = f"QUARTERLY SELL SIGNAL using {quarterly_pdf_path}"
    else:
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
        stock['enterprise_value'] = info.get('enterpriseValue', 'N/A')
        stock['ebitda'] = info.get('ebitda', 'N/A')
        
        # Growth and Health Metrics
        stock['revenue_growth'] = info.get('revenueGrowth', 'N/A')
        stock['profit_margins'] = info.get('profitMargins', 'N/A')
        stock['operating_margins'] = info.get('operatingMargins', 'N/A')
        stock['return_on_equity'] = info.get('returnOnEquity', 'N/A')
        stock['total_debt'] = info.get('totalDebt', 'N/A')
        stock['debt_to_equity'] = info.get('debtToEquity', 'N/A')
        stock['free_cashflow'] = info.get('freeCashflow', 'N/A')
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

    previous_thesis = None
    if quarterly_mode:
        md_path_deep = os.path.join(company_dir, "Analysis.md")
        if os.path.exists(md_path_deep):
            try:
                with open(md_path_deep, "r", encoding="utf-8") as f:
                    previous_thesis = f.read()
            except Exception as e:
                logger.error(f"Failed to read previous thesis for {ticker}: {e}")

    ai_client = gemini_client or GeminiClient()
    
    analysis = None
    if lite_mode or quarterly_mode:
        # Fallback to the old monolithic prompt for lite/quarterly for now, 
        # as the new architecture is strictly for the Deep Dive Annual Report.
        analysis = ai_client.analyze_stock(stock, lite_mode, custom_question, doc_age_months, quarterly_mode, previous_thesis, quarterly_pdf_path)
    else:
        # --- NEW AGENTIC INGESTION PIPELINE ---
        logger.info(f"Initiating Multi-Agent Ingestion Pipeline for {ticker}...")
        # 1. Upload the file once to the staging area
        gemini_file = None
        cached_content = None
        temp_pdf_path = None
        try:
             # Sanitize the display name to pure ASCII for both Upload and Cache.
             # The Gemini API throws UnicodeEncodeError if it encounters chars like 'Å'
             raw_name = f"File_{ticker}_{os.path.basename(pdf_path)}"
             safe_name = raw_name.encode("ascii", "ignore").decode("ascii")
             
             # Create a physical temporary file with a pure ASCII name to bypass SDK multipart bugs
             temp_pdf_path = os.path.join(tempfile.gettempdir(), f"{safe_name}.pdf")
             shutil.copy2(pdf_path, temp_pdf_path)
             
             logger.info(f"Uploading {pdf_path} to Gemini Staging as {safe_name}...")
             gemini_file = ai_client.client.files.upload(
                 file=temp_pdf_path,
                 config={'display_name': safe_name[:128]}
             )
             
             if os.path.exists(temp_pdf_path):
                 os.remove(temp_pdf_path)
                 
             # 2. Freeze the context into a Cache to save tokens on multiple agent passes
             if gemini_file:
                 # We use the first model in the list (or a default) to bind the cache to
                 from core.config import GEMINI_MODELS
                 cache_model = GEMINI_MODELS[0] if GEMINI_MODELS else "models/gemini-1.5-pro-002"
                 
                 cache_name = f"Cache_{ticker}_{os.path.basename(pdf_path)}"
                 safe_cache_name = cache_name.encode("ascii", "ignore").decode("ascii")
                 
                 cached_content = ai_client.create_cached_content(
                     model_name=cache_model, 
                     file_uri=gemini_file.uri, 
                     display_name=safe_cache_name
                 )
        except Exception as e:
             if temp_pdf_path and os.path.exists(temp_pdf_path):
                 os.remove(temp_pdf_path)
             logger.error(f"Upload or Cache creation failed for {pdf_path}: {e}")
             return
             
        if gemini_file:
            try:
                # 3. Table Extraction (Using Cache if available)
                table_agent = TableExtractionAgent(ai_client)
                table_data = table_agent.extract(stock['name'], gemini_file=gemini_file, cached_content=cached_content)
                
                # 4. Critic Validation
                critic = CriticValidator()
                is_valid, errors = critic.validate(table_data)
                
                if not is_valid:
                    logger.error(f"Pipeline Halted: Critic Validation Failed for {ticker}. Errors: {errors}")
                    return
                    
                # 5. Narrative Extraction (Using the exact same Cache, saving 100k+ input tokens)
                narrative_agent = NarrativeForensicAgent(ai_client)
                narrative_data = narrative_agent.extract(stock['name'], gemini_file=gemini_file, cached_content=cached_content)
                
                # 6. Synthesis Agent (Final Formatting - No PDF needed here)
                synthesis_agent = SynthesisAgent(ai_client)
                final_report = synthesis_agent.synthesize(stock['name'], table_data, narrative_data, stock)
            
            finally:
                # 7. Cleanup! This is critical to avoid paying for hanging cache storage
                if cached_content:
                    try:
                        logger.info(f"Deleting Context Cache {cached_content.name}...")
                        cached_content.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete cache: {e}")
                
                # Optional: Delete the underlying file too if you don't want it accumulating
                # try:
                #     gemini_file.delete()
                # except:
                #     pass
            
            # 6. Map to UI format
            if final_report:
                analysis = {
                    "recommendation": final_report.recommendation,
                    "conviction_score": str(final_report.conviction_score), 
                    "is_10_bagger_candidate": final_report.is_10_bagger_candidate,
                    "global_thought": final_report.global_thought,
                    "verdict_summary": final_report.verdict_summary,
                    "analysis": final_report.analysis.model_dump()
                }
            else:
                 logger.error("SynthesisAgent failed!")
                 return
        
    if analysis:
        generate_markdown_report(company_dir, ticker, stock, analysis, lite_mode=lite_mode, custom_question=custom_question, quarterly_mode=quarterly_mode, quarterly_pdf_path=quarterly_pdf_path)
        if not quarterly_mode:
            db.save_analysis(stock['isin'], analysis, lite_mode=lite_mode)
        print(f"Success! Analysis complete for {ticker} ({mode_name}).")
    else:
        logger.error(f"Analysis failed for {ticker}")


def run_launchpad_batch(limit: int = 5, gemini_client: Optional[GeminiClient] = None):
    """Processes a batch of high-potential Launchpad candidates."""
    candidates = db.get_launchpad_candidates(limit)
    logger.info(f"Starting analysis for {len(candidates)} candidates.")
    
    ai_client = gemini_client or GeminiClient()
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
