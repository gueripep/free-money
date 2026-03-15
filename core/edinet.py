import os
import requests
import json
import csv
import io
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from core.config import DATA_DIR, setup_logging

logger = setup_logging("edinet")

# Configuration
EDINET_MAPPING_FILE = os.path.join(DATA_DIR, "edinet_mapping.json")
EDINET_OVERRIDES_FILE = os.path.join(DATA_DIR, "edinet_overrides.json")
EDINET_CACHE_DIR = os.path.join(DATA_DIR, "edinet_cache")
EDINET_CODE_LIST_URL = "https://raw.githubusercontent.com/kenpos/StockAnalystic/master/EdinetcodeDlInfo.csv"
API_VERSION = "v2"
BASE_URL = f"https://api.edinet-fsa.go.jp/api/{API_VERSION}"

os.makedirs(EDINET_CACHE_DIR, exist_ok=True)

class EdinetClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EDINET_API_KEY")
        if not self.api_key:
            logger.warning("EDINET_API_KEY not found in environment. API calls will fail.")
        self.mapping_data = self._load_mapping_data()

    def _load_mapping_data(self) -> Dict[str, Dict]:
        """Loads or downloads the Ticker-to-EDINET mapping and metadata."""
        if os.path.exists(EDINET_MAPPING_FILE):
            with open(EDINET_MAPPING_FILE, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        else:
            mapping = self._download_and_build_mapping()

        # Apply overrides
        if os.path.exists(EDINET_OVERRIDES_FILE):
            try:
                with open(EDINET_OVERRIDES_FILE, 'r', encoding='utf-8') as f:
                    overrides = json.load(f)
                    mapping.update(overrides)
                    logger.info(f"Applied {len(overrides)} EDINET mapping overrides from {os.path.basename(EDINET_OVERRIDES_FILE)}")
            except Exception as e:
                logger.error(f"Error loading EDINET overrides: {e}")
        
        return mapping

    def _download_and_build_mapping(self) -> Dict[str, Dict]:
        """Downloads the Ticker-to-EDINET mapping and builds the initial dictionary."""
        try:
            response = requests.get(EDINET_CODE_LIST_URL)
            if response.status_code != 200:
                logger.error(f"Failed to download EDINET mapping: {response.status_code}")
                return {}
            
            mapping = {}
            content = response.content.decode('ms932', errors='replace')
            reader = csv.reader(io.StringIO(content))
            
            rows = list(reader)
            start_idx = 0
            for i, row in enumerate(rows):
                if row and row[0] == "EDINETコード":
                    start_idx = i + 1
                    break
            
            # Columns: EDINETコード (0), ..., 決算日 (5), 提出者名 (6), ... 証券コード (11)
            for row in rows[start_idx:]:
                if len(row) > 11:
                    edinet_code = row[0]
                    fiscal_end = row[5] # e.g. "3月31日"
                    sec_code = row[11].strip()
                    if sec_code:
                        ticker = sec_code[:4]
                        mapping[ticker] = {
                            "edinet_code": edinet_code,
                            "fiscal_end": fiscal_end,
                            "name": row[6]
                        }
            
            with open(EDINET_MAPPING_FILE, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=4)
            
            logger.info(f"Successfully created EDINET mapping for {len(mapping)} tickers.")
            return mapping
        except Exception as e:
            logger.error(f"Error building EDINET mapping: {e}")
            return {}

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Gets mapping data for a ticker."""
        clean_ticker = ticker.split('.')[0].strip()
        info = self.mapping_data.get(clean_ticker)
        if not info:
             logger.warning(f"Ticker {clean_ticker} not found in EDINET mapping. You can add it manually to {os.path.basename(EDINET_OVERRIDES_FILE)}.")
        return info

    def download_document(self, doc_id: str, save_path: str) -> bool:
        """Downloads a PDF document from EDINET."""
        if not self.api_key:
            return False
            
        url = f"{BASE_URL}/documents/{doc_id}"
        params = {
            "type": "2", # PDF
            "Subscription-Key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                logger.error(f"Failed to download document {doc_id}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error downloading document {doc_id}: {e}")
            return False

    def get_document_list(self, date: datetime) -> List[Dict]:
        """Fetches the document list for a specific date, with local caching."""
        if not self.api_key:
            return []
            
        date_str = date.strftime("%Y-%m-%d")
        cache_path = os.path.join(EDINET_CACHE_DIR, f"{date_str}.json")
        
        # Check cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading cache for {date_str}: {e}")

        url = f"{BASE_URL}/documents.json"
        params = {
            "date": date_str,
            "type": "2", # Metadata + List
            "Subscription-Key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Cache the results
                # Only cache if it's not today's list (which might change)
                if date.date() < datetime.now().date():
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False)
                
                return results
            else:
                logger.error(f"Failed to fetch document list for {date_str}: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching document list for {date_str}: {e}")
            return []

    def find_latest_report(self, ticker: str, form_codes: List[str], max_lookback_days: int = 500) -> Optional[Dict]:
        """
        Scans recent days to find the latest report of a specific type (by form_code) for a ticker.
        Common Form Codes:
        - 030000: Annual Securities Report (Yuho)
        - 043000: Quarterly Securities Report (Shihanki)
        - 043A00: Semi-annual Securities Report (Hanki - e.g., foreign/special entities)
        - 050000: Interim Securities Report (Hanki)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        info = self.get_company_info(ticker)
        if not info:
            logger.error(f"No EDINET info found for ticker {ticker}")
            return None
            
        target_edinet_code = info["edinet_code"]
        current_date = datetime.now()
        
        logger.info(f"Searching for latest report (codes: {form_codes}) for {ticker} ({target_edinet_code}) over last {max_lookback_days} days...")

        # Batch days for parallel processing
        batch_size = 15
        for i in range(0, max_lookback_days, batch_size):
            dates_to_check = []
            for j in range(batch_size):
                day_offset = i + j
                if day_offset >= max_lookback_days: break
                
                search_date = current_date - timedelta(days=day_offset)
                if search_date.weekday() < 5: # Only weekdays
                    dates_to_check.append(search_date)
            
            if not dates_to_check: continue
                
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_date = {executor.submit(self.get_document_list, d): d for d in dates_to_check}
                
                results_by_date = {}
                for future in as_completed(future_to_date):
                    search_date = future_to_date[future]
                    try:
                        docs = future.result()
                        results_by_date[search_date] = docs
                    except Exception as e:
                        logger.error(f"Parallel search error for {search_date}: {e}")
                
                # Check results in descending order of date in this batch
                for search_date in sorted(dates_to_check, reverse=True):
                    docs = results_by_date.get(search_date, [])
                    for doc in docs:
                        if doc.get("edinetCode") == target_edinet_code and doc.get("formCode") in form_codes:
                            logger.info(f"Found report filed on {search_date.strftime('%Y-%m-%d')}: {doc['docID']}")
                            return {
                                "doc_id": doc["docID"],
                                "date": search_date.strftime("%Y-%m-%d"),
                                "title": doc.get("docDescription"),
                                "form_code": doc.get("formCode")
                            }
        
        logger.warning(f"No report (codes: {form_codes}) found for {ticker} in the last {max_lookback_days} days.")
        return None

    def find_latest_yuho(self, ticker: str, max_lookback_days: int = 500) -> Optional[Dict]:
        """Search for the latest Annual Securities Report (Yuho)."""
        return self.find_latest_report(ticker, ["030000"], max_lookback_days)
