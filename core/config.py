import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Config & Directories ---
# Since config.py is now in core/, the project root is one level up
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
COMPANIES_DIR = os.path.join(DATA_DIR, "companies")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# DB & Data files
DB_FILE = os.path.join(DATA_DIR, "stocks.db")
UPLOAD_CSV = os.path.join(DATA_DIR, "ingest_batch.csv")
TICKERS_JSON = os.path.join(DATA_DIR, "tickers.json")

# Ensure required directories exist
for d in [DATA_DIR, REPORTS_DIR, COMPANIES_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODELS = [
    "models/gemini-3-flash-preview",
    "models/gemini-3.1-pro-preview",
    "models/gemini-2.5-pro"
]

# Logging setup
def setup_logging(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(os.path.join(LOGS_DIR, f"{name}.log"))
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(formatter)
        f_handler.setFormatter(formatter)
        
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
        
    return logger
