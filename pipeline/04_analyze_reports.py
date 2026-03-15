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
from ai.score_auditor import ScoreAuditor
from ai.blind_agents import BlindExtractionAgent, BlindEvaluationAgent
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
        f.write(f"**Source Document:** {source}\n\n")
        
        details = analysis.get('analysis', {})
        
        if quarterly_mode:
            # --- Quarterly mode: verdict at top is fine (it's a check, not a thesis) ---
            f.write(f"**Thesis Holds:** {'YES' if analysis.get('thesis_holds') else 'NO'}\n")
            f.write(f"**Recommendation:** {analysis.get('recommendation', 'N/A')}\n\n")
            f.write("## Executive Summary\n")
            f.write(f"{analysis.get('verdict_summary', 'N/A')}\n\n")
            f.write("## 1. Global Synthesis & Business Reality\n")
            f.write(f"{analysis.get('global_thought', 'N/A')}\n\n")
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
            # --- Lite mode: simple summary format ---
            f.write(f"**Conviction Score:** {analysis.get('conviction_score', 'N/A')}/5\n")
            f.write(f"**Verdict:** {analysis.get('recommendation', 'N/A')}\n\n")
            f.write("## 📖 What Does This Company Actually Do?\n")
            f.write(f"{details.get('company_introduction', 'N/A')}\n\n")
            f.write("## 🚀 The Catalyst (Why are the numbers popping?)\n")
            f.write(f"{details.get('catalyst_explanation', 'N/A')}\n\n")
            f.write("## 🔬 Reality Check (Metrics & Valuation)\n")
            f.write(f"{details.get('metrics_and_valuation', 'N/A')}\n\n")
            f.write("## 🚩 The Catch (Risks & Unknowns)\n")
            f.write(f"{details.get('risks_and_unknowns', 'N/A')}\n\n")
            f.write("## 💡 Final Takeaway\n")
            f.write(f"{analysis.get('verdict_summary', 'N/A')}\n\n")
        else:
            # --- DEEP DIVE: Evidence first, verdict last ---
            
            # Section 1: Company Introduction (opens the document, no verdict, no framing)
            f.write("## 1. Company Introduction\n")
            f.write(f"{details.get('company_introduction', 'N/A')}\n\n")
            
            # Sections 2-7: The evidence
            f.write("## 2. The Forensic Launchpad (Financials)\n")
            f.write(f"{details.get('forensic_launchpad', 'N/A')}\n\n")
            
            f.write("## 3. Competitive Moat\n")
            f.write(f"{details.get('competitive_moat', 'N/A')}\n\n")
            
            f.write("## 4. Growth Catalysts & Risks\n")
            f.write(f"{details.get('growth_catalysts_and_risks', 'N/A')}\n\n")
            
            f.write("## 5. Management Quality\n")
            f.write(f"{details.get('management_quality', 'N/A')}\n\n")
            
            f.write("## 6. Valuation\n")
            f.write(f"{details.get('valuation', 'N/A')}\n\n")
            
            f.write("## 7. Red Flags\n")
            f.write(f"{details.get('red_flags', 'N/A')}\n\n")
            
            # Section 8: Scorecard (the mathematical basis for the verdict)
            f.write("## 8. Conviction Scorecard\n")
            f.write(f"{details.get('conviction_scorecard', 'N/A')}\n\n")
            
            # Section 9: Hard reconciliation (must come before verdict)
            f.write("## 9. Where the Bull and Bear Cases Disagree\n")
            f.write(f"{details.get('bull_bear_disagreements', 'N/A')}\n\n")
            
            # Section 10: Pre-mortem
            f.write("## 10. Pre-Mortem (The Bear Case)\n")
            f.write(f"{details.get('pre_mortem', 'N/A')}\n\n")
            

            
            # --- VERDICT (appears LAST, derived from the scorecard above) ---
            f.write("---\n\n")
            f.write("## Investment Conclusion\n\n")
            f.write(f"**Conviction Score:** {analysis.get('conviction_score', 'N/A')}/5\n")
            f.write(f"**10-Bagger Candidate:** {'YES' if analysis.get('is_10_bagger_candidate') else 'NO'}\n")
            f.write(f"**Verdict:** {analysis.get('recommendation', 'N/A')}\n\n")
            f.write(f"{analysis.get('verdict_summary', 'N/A')}\n\n")
            f.write(f"### Synthesis\n")
            f.write(f"{analysis.get('global_thought', 'N/A')}\n\n")
            
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
                    mime_type=gemini_file.mime_type,
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
                
                if not table_data:
                    logger.error(f"Pipeline Halted: Table Extraction returned None for {ticker}.")
                    return

                # 4. Critic Validation
                critic = CriticValidator()
                is_valid, errors = critic.validate(table_data)
                
                if not is_valid:
                    logger.error(f"Pipeline Halted: Critic Validation Failed for {ticker}. Errors: {errors}")
                    return
                    
                # 5. Narrative Extraction (Using the exact same Cache, saving 100k+ input tokens)
                narrative_agent = NarrativeForensicAgent(ai_client)
                narrative_data = narrative_agent.extract(stock['name'], gemini_file=gemini_file, cached_content=cached_content)
                
                # 6. Blind Qualitative Analysis (Two-Pass)
                logger.info(f"Running Blind Qualitative Analysis for {ticker}...")
                blind_extraction_agent = BlindExtractionAgent(ai_client)
                blind_extraction_data = blind_extraction_agent.extract(stock['name'], gemini_file=gemini_file, cached_content=cached_content)
                
                blind_evaluation_data = None
                if blind_extraction_data:
                    blind_evaluation_agent = BlindEvaluationAgent(ai_client)
                    blind_evaluation_data = blind_evaluation_agent.evaluate(blind_extraction_data)
                
                # 7. Synthesis Agent (Final Formatting - No PDF needed here)
                synthesis_agent = SynthesisAgent(ai_client)
                final_report = synthesis_agent.synthesize(stock['name'], table_data, narrative_data, blind_evaluation_data, stock)
                
                # 8. Score Auditor (Devil's Advocate calibration)
                if final_report:
                    logger.info(f"Initiating Score Audit for {ticker}...")
                    auditor = ScoreAuditor(ai_client)
                    audit_results = auditor.audit(stock['name'], final_report)
                    
                    if audit_results and audit_results.any_overrides:
                        logger.warning(f"Auditor Adjusted Scores for {ticker}: {audit_results.adjustments_made}")
                        final_report.score_revenue_growth_quality = audit_results.score_revenue_growth_quality
                        final_report.score_moat_durability = audit_results.score_moat_durability
                        final_report.score_capital_efficiency = audit_results.score_capital_efficiency
                        final_report.score_management_quality = audit_results.score_management_quality
                        final_report.score_risk_profile = audit_results.score_risk_profile
                        
                        # Regenerate the scorecard table for consistency in the report
                        new_table = "| Dimension | Score | Weight | Weighted Score |\n| :--- | :--- | :--- | :--- |\n"
                        new_table += f"| Revenue Growth Quality | {audit_results.score_revenue_growth_quality} | 25% | {round(audit_results.score_revenue_growth_quality * 0.25, 2)} |\n"
                        new_table += f"| Moat Durability | {audit_results.score_moat_durability} | 25% | {round(audit_results.score_moat_durability * 0.25, 2)} |\n"
                        new_table += f"| Capital Efficiency | {audit_results.score_capital_efficiency} | 20% | {round(audit_results.score_capital_efficiency * 0.20, 2)} |\n"
                        new_table += f"| Management Quality | {audit_results.score_management_quality} | 15% | {round(audit_results.score_management_quality * 0.15, 2)} |\n"
                        new_table += f"| Risk Profile | {audit_results.score_risk_profile} | 15% | {round(audit_results.score_risk_profile * 0.15, 2)} |\n"
                        computed_conviction = round(
                            0.25 * audit_results.score_revenue_growth_quality +
                            0.25 * audit_results.score_moat_durability +
                            0.20 * audit_results.score_capital_efficiency +
                            0.15 * audit_results.score_management_quality +
                            0.15 * audit_results.score_risk_profile,
                            2
                        )
                        new_table += f"| **Final Conviction Score** | | **100%** | **{computed_conviction}** |\n"
                        final_report.analysis.conviction_scorecard = new_table
                    else:
                        logger.info(f"Audit Complete for {ticker}: No overrides needed.")
            
            finally:
                # 7. Cleanup! This is critical to avoid paying for hanging cache storage
                if cached_content:
                    try:
                        logger.info(f"Deleting Context Cache {cached_content.name}...")
                        ai_client.client.caches.delete(name=cached_content.name)
                    except Exception as e:
                        logger.error(f"Failed to delete cache: {e}")
                
                # Optional: Delete the underlying file too if you don't want it accumulating
                # try:
                #     gemini_file.delete()
                # except:
                #     pass
            
            # 6. Map to UI format
            if final_report:
                # Compute conviction score from sub-scores using the prescribed weights
                computed_conviction = round(
                    0.25 * final_report.score_revenue_growth_quality +
                    0.25 * final_report.score_moat_durability +
                    0.20 * final_report.score_capital_efficiency +
                    0.15 * final_report.score_management_quality +
                    0.15 * final_report.score_risk_profile,
                    2
                )
                analysis = {
                    "recommendation": final_report.recommendation,
                    "score_revenue_growth_quality": final_report.score_revenue_growth_quality,
                    "score_moat_durability": final_report.score_moat_durability,
                    "score_capital_efficiency": final_report.score_capital_efficiency,
                    "score_management_quality": final_report.score_management_quality,
                    "score_risk_profile": final_report.score_risk_profile,
                    "conviction_score": str(computed_conviction),
                    "is_10_bagger_candidate": final_report.is_10_bagger_candidate,
                    "global_thought": final_report.global_thought,
                    "verdict_summary": final_report.verdict_summary,
                    "analysis": final_report.analysis.model_dump(),
                    "structural_quality_blind": final_report.structural_quality_blind.model_dump() if final_report.structural_quality_blind else None
                }
            else:
                 logger.error("SynthesisAgent failed!")
                 return
        
    if analysis:
        generate_markdown_report(company_dir, ticker, stock, analysis, lite_mode=lite_mode, custom_question=custom_question, quarterly_mode=quarterly_mode, quarterly_pdf_path=quarterly_pdf_path)
        if not quarterly_mode:
            db.save_analysis(stock['isin'], analysis, lite_mode=lite_mode)
        print(f"Success! Analysis complete for {ticker} ({mode_name}).")
        
        # Log total usage report at the end
        logger.info(ai_client.get_usage_report())
        print(ai_client.get_usage_report())
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
