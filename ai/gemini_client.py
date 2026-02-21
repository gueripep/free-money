import os
import json
import datetime
from google import genai
from google.genai import types
from typing import Dict, Optional, List
from core.config import GEMINI_API_KEY, GEMINI_MODELS, DATA_DIR, setup_logging
from ai.prompts import get_exponential_returns_prompt, get_lite_analysis_prompt, get_quarterly_update_prompt

logger = setup_logging("gemini_client")

class GeminiClient:
    def __init__(self):
        self.client = None
        if GEMINI_API_KEY:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            logger.error("GEMINI_API_KEY not found in environment.")
        
        self.blacklist_file = os.path.join(DATA_DIR, "model_blacklist.json")

    def _is_model_blacklisted(self, model_name: str) -> bool:
        if not os.path.exists(self.blacklist_file):
            return False
        try:
            with open(self.blacklist_file, "r") as f:
                blacklist = json.load(f)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            return blacklist.get(model_name) == today
        except Exception as e:
            logger.error(f"Error reading blacklist: {e}")
            return False
            
    def _blacklist_model(self, model_name: str):
        blacklist = {}
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file, "r") as f:
                    blacklist = json.load(f)
            except Exception:
                pass
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        blacklist[model_name] = today
        try:
            with open(self.blacklist_file, "w") as f:
                json.dump(blacklist, f)
            logger.warning(f"Blacklisted model {model_name} for today ({today}).")
        except Exception as e:
            logger.error(f"Error writing blacklist: {e}")

    def analyze_stock(self, stock: dict, lite_mode: bool = False, custom_question: str = None, doc_age_months: int = None, quarterly_mode: bool = False, previous_thesis: str = None, quarterly_pdf_path: str = None) -> Optional[dict]:
        """Runs the deep dive analysis on a stock, optionally using Lite search mode instead of PDF uploads."""
        
        gemini_files = []
        doc_names = []
        
        if quarterly_mode and quarterly_pdf_path and os.path.exists(quarterly_pdf_path):
            logger.info("Quarterly Mode requested.")
            try:
                logger.info(f"Uploading {quarterly_pdf_path} to Gemini...")
                g_file = self.client.files.upload(file=quarterly_pdf_path)
                gemini_files.append(g_file)
                doc_names.append(os.path.basename(quarterly_pdf_path))
            except Exception as e:
                logger.error(f"Upload failed for {quarterly_pdf_path}: {e}")
            
            prompt_text = get_quarterly_update_prompt(stock, doc_names, previous_thesis, custom_question)
        elif not lite_mode:
            # 1. Upload reports (Annual over Quarterly for Deep Divve)
            for path_key in ['annual_report_path', 'quarterly_report_path']:
                path = stock.get(path_key)
                if path and os.path.exists(path):
                    try:
                        logger.info(f"Uploading {path} to Gemini...")
                        g_file = self.client.files.upload(file=path)
                        gemini_files.append(g_file)
                        doc_names.append(os.path.basename(path))
                    except Exception as e:
                        logger.error(f"Upload failed for {path}: {e}")

            # 2. Construct Prompt
            prompt_text = get_exponential_returns_prompt(stock, doc_names, custom_question, doc_age_months)
        else:
            logger.info("Lite Mode requested. Skipping PDF uploads.")
            prompt_text = get_lite_analysis_prompt(stock, custom_question)
            
        prompt = [prompt_text]
        if not lite_mode or quarterly_mode:
            prompt.extend(gemini_files)

        for model_name in GEMINI_MODELS:
            if self._is_model_blacklisted(model_name):
                logger.warning(f"Skipping {model_name} - Blacklisted for today.")
                continue

            logger.info(f"Attempting analysis with {model_name}...")
            
            try:
                if not self.client:
                    logger.error("Gemini client not initialized.")
                    return None
                    
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text.replace("```json", "", 1).replace("```", "", 1).strip()
                
                analysis_data = json.loads(text)
                
                # Handle list wrapper
                if isinstance(analysis_data, list):
                    if len(analysis_data) > 0:
                        analysis = analysis_data[0]
                    else:
                        logger.error("Analysis returned empty list")
                        return None
                else:
                    analysis = analysis_data

                return analysis
            except Exception as e:
                logger.error(f"Analysis failed with {model_name}: {e}")
                self._blacklist_model(model_name)
        
        logger.error("All available models failed or were blacklisted.")
        return None

    def generate_tier_list_text(self, prompt_text: str, files: List[str] = None) -> Optional[str]:
        """Generates raw Markdown text for the Tier List analysis or final ranking without forcing JSON output."""
        gemini_files = []
        if files:
            for path in files:
                if os.path.exists(path):
                    try:
                        logger.info(f"Uploading {path} to Gemini for Tier List...")
                        g_file = self.client.files.upload(file=path)
                        gemini_files.append(g_file)
                    except Exception as e:
                        logger.error(f"Upload failed for {path}: {e}")

        prompt = [prompt_text]
        prompt.extend(gemini_files)

        for model_name in GEMINI_MODELS:
            if self._is_model_blacklisted(model_name):
                logger.warning(f"Skipping {model_name} - Blacklisted for today.")
                continue

            logger.info(f"Attempting Tier List generation with {model_name}...")
            
            try:
                if not self.client:
                    logger.error("Gemini client not initialized.")
                    return None
                    
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                
                return response.text.strip()
            except Exception as e:
                logger.error(f"Tier List generation failed with {model_name}: {e}")
                self._blacklist_model(model_name)
        
        logger.error("All available models failed to generate Tier List text.")
        return None
    def extract_calendar_events(self, pdf_path: str, current_date: str) -> List[Dict]:
        """Extracts corporate events from a PDF using Gemini and the calendar prompt."""
        from ai.prompts import get_calendar_extraction_prompt
        
        if not os.path.exists(pdf_path):
            logger.error(f"PDF path does not exist: {pdf_path}")
            return []

        try:
            logger.info(f"Uploading {pdf_path} for event extraction...")
            g_file = self.client.files.upload(file=pdf_path)
            
            prompt_text = get_calendar_extraction_prompt(current_date)
            
            for model_name in GEMINI_MODELS:
                if self._is_model_blacklisted(model_name):
                    continue
                
                try:
                    logger.info(f"Attempting event extraction with {model_name}...")
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[prompt_text, g_file],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text.replace("```json", "", 1).replace("```", "", 1).strip()
                    
                    events = json.loads(text)
                    return events if isinstance(events, list) else []
                except Exception as e:
                    logger.error(f"Event extraction failed with {model_name}: {e}")
                    self._blacklist_model(model_name)
                    
        except Exception as e:
            logger.error(f"Event extraction process failed: {e}")
            
        return []
