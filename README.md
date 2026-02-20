# 10-Bagger Stock Finder (PEA-PME)

A deep document analysis pipeline using **Gemini 3 Flash Preview** to identify high-growth stocks in the European PEA-PME market.

## Project Structure

- **`config.py`**: Centralized configuration for paths, logging, and environment variables.
- **`scraper.py`**: Downloads and parses the official Euronext PEA-PME Excel list.
- **`data_fetcher.py`**: Ingests financial ratios and 5y price history into SQLite via `yfinance`.
- **`report_manager.py`**: Automates discovery and download of the latest PDF financial reports (2025/2026).
- **`analyzer.py`**: Performs deep synthesis of multiple PDF reports using Gemini 3.
- **`data/`**: contains `stocks.db` and downloaded PDF reports.

## Getting Started

1. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Ingest Tickers**:
   ```powershell
   python scraper.py
   ```

3. **Fetch Financial Ratios**:
   ```powershell
   python data_fetcher.py
   ```

4. **Run Deep Analysis**:
   ```powershell
   python analyzer.py
   ```

## Key Features
- **Tiered Analysis**: Automatically filters the 1,300+ stocks down to the top ~50 candidates before running expensive document synthesis (~$0.20 per stock).
- **Multi-Document Context**: Gemini 3 analyzes the **Annual Report** (strategy) and **Quarterly/Interim Report** (execution) simultaneously in a 1M token window.
- **Recency Priority**: Automatically prioritizes 2025 and 2026 documents to ensure up-to-date investment verdicts.
