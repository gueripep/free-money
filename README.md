# 10-Bagger Stock Finder (PEA-PME)

A deep quantitative and narrative analysis pipeline using **Gemini** to identify high-growth stocks in the European PEA-PME market.

This project automates the process of finding "10-Bagger" candidates by filtering the Euronext PEA-PME index based on strict quantitative metrics, followed by AI-powered forensic analysis of official financial reports.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- A Google API Key for [Gemini AI Studio](https://aistudio.google.com/).
- Install dependencies:
  ```powershell
  pip install -r requirements.txt
  ```

### 2. Launch the Application
Start the Streamlit dashboard as your primary control center:
```powershell
python -m streamlit run ui/app.py
```

### 3. Setup Your API Key
In the **sidebar**, enter your Gemini API Key in the "Security & Configuration" section. This persists for your session and allows you to run AI features without needing a `.env` file for local development.

## 📥 Ingestion Workflow

The ingestion process is now a **unified, one-click experience** via the UI:

1.  **🛰️ The Scanner Tab**: Upload a CSV containing at least a `Ticker` or `ISIN` column.
2.  **🚀 Start Batch Ingestion**: Click this single button to trigger:
    - Automatic CSV parsing and local storage.
    - Automatic ISIN-to-Ticker resolution via `yfinance`.
    - Real-time fetching of financial metrics (Margins, Cap, Growth, etc.).
    - Initial population of the local database (`data/stocks.db`).

## 🛠️ Data Management

- **Global Refresh**: In the sidebar, use "🔄 Refresh All Portfolio Metrics" to update price and ratio data for all stocks already in your database.
- **Mathematical Tier List**: Use "🏆 Global Mathematical Ranking" to evaluate your entire universe against the *Calculus of Outperformance*. This orders candidates by statistical probability of 10x potential.

## 🛩️ The Cockpit (Analysis Workflow)

1.  **Deep Dive Selection**: Tickers are ordered by their **Mathematical Composite Score**. Focus on the top first.
2.  **Manual Verdicts**: Assign a manual grade (🔴 Bad, 🟡 Maybe, 🟢 Good) to filter your list.
3.  **AI Synthesis**:
    - **Lite Search**: Real-time AI analysis based on Live Yahoo Finance data.
    - **Full Report Analysis**: Upload an Annual Report (PDF) for Gemini to extract moat analysis, narrative red flags, and competitive advantage.
    - **Sell Signal Monitoring**: Analyze Interim/Quarterly reports to check if your initial investment thesis still holds true.

---
**Note**: All AI-generated analyses are saved locally in `data/companies/<TICKER>/` for permanent offline access.
