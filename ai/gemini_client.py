import os
import json
import datetime
import google.generativeai as genai
from typing import Dict, Optional, List
from core.config import GEMINI_API_KEY, GEMINI_MODELS, DATA_DIR, setup_logging
from ai.prompts import get_exponential_returns_prompt, get_lite_analysis_prompt

logger = setup_logging("gemini_client")

class GeminiClient:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
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

    def analyze_stock(self, stock: dict, lite_mode: bool = False, custom_question: str = None, doc_age_months: int = None) -> Optional[dict]:
        """Runs the deep dive analysis on a stock, optionally using Lite search mode instead of PDF uploads."""
        
        gemini_files = []
        doc_names = []
        
        if not lite_mode:
            # 1. Upload reports (Annual over Quarterly for Deep Divve)
            for path_key in ['annual_report_path', 'quarterly_report_path']:
                path = stock.get(path_key)
                if path and os.path.exists(path):
                    try:
                        logger.info(f"Uploading {path} to Gemini...")
                        g_file = genai.upload_file(path=path)
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
        if not lite_mode:
            prompt.extend(gemini_files)

        for model_name in GEMINI_MODELS:
            if self._is_model_blacklisted(model_name):
                logger.warning(f"Skipping {model_name} - Blacklisted for today.")
                continue

            logger.info(f"Attempting analysis with {model_name}...")
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={"response_mime_type": "application/json"}
            )
            
            try:
                response = model.generate_content(prompt)
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
