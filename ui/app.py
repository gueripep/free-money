import os
import sys

# Define PROJECT_ROOT immediately
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from urllib.parse import quote_plus
import json
import subprocess
from datetime import datetime
import importlib
import importlib.util
import core.database as db
from core.config import COMPANIES_DIR, DATA_DIR
from ai.gemini_client import GeminiClient

# Initialize Gemini Client (uses GEMINI_API_KEY from .env by default)
gemini = GeminiClient()

# Pipeline Imports via importlib
def load_pipeline_module(module_name, filename):
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(PROJECT_ROOT, "pipeline", filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

analyze_reports = load_pipeline_module("analyze_reports", "04_analyze_reports.py")
rank_candidates = load_pipeline_module("rank_candidates", "03_rank_candidates.py")
ingest_stocks = load_pipeline_module("ingest_stocks", "01_ingest_stocks.py")
fetch_financials = load_pipeline_module("fetch_financials", "02_fetch_financials.py")

# Initialize Database
db.init_db()

# Page configuration
st.set_page_config(page_title="10-Bagger Discovery", page_icon="📈", layout="wide")

# Removed frontend API Key Management per user request

# --- Background Ingestion Monitoring ---
def is_ingestion_running():
    lock_file = os.path.join(DATA_DIR, ".ingestion.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError, FileNotFoundError, OSError):
            return False
    return False

def get_ingestion_stats():
    """Returns (finished_count, total_count) for the progress bar."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # Count refreshed in last 24h (the 'done' part)
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE last_updated >= datetime('now', '-1 day')")
        refreshed = cursor.fetchone()[0]
        # Count total stocks in database (the 'total' part)
        cursor.execute("SELECT COUNT(*) FROM stocks")
        total = cursor.fetchone()[0]
        conn.close()
        return refreshed, total
    except Exception:
        return 0, 0

st.sidebar.markdown("---")
st.sidebar.title("🛠️ Data Control Center")

from core.config import UPLOAD_CSV
uploaded_csv = st.sidebar.file_uploader("Batch Ingest (Upload CSV)", type="csv", help="CSV must have a 'Ticker' or 'ISIN' column.")
if uploaded_csv:
    with open(UPLOAD_CSV, "wb") as f:
        f.write(uploaded_csv.getbuffer())
    st.sidebar.success(f"File `{uploaded_csv.name}` ready!")

running = is_ingestion_running()

if st.sidebar.button("🚀 Sync & Update Database", use_container_width=True, help="Ingests new CSV data and refreshes stale/missing metrics.", disabled=running):
    # Launch pipeline/run_full_sync.py as a background process
    # This script handles its own lock and running both phases
    script_path = os.path.join(PROJECT_ROOT, "pipeline", "run_full_sync.py")
    subprocess.Popen([sys.executable, script_path], start_new_session=True)
    st.toast("Background sync triggered!")
    st.rerun()

st.sidebar.markdown("---")

@st.fragment(run_every=5)
def ingestion_status_bar():
    is_running = is_ingestion_running()
    refreshed, total = get_ingestion_stats()
    
    if is_running:
        st.info("🚀 Background Ingestion Running")
        st.progress(refreshed / max(total, 1), text=f"{refreshed}/{total} Updated")
        if st.button("Stop Ingestion", use_container_width=True):
            lock_file = os.path.join(DATA_DIR, ".ingestion.lock")
            try:
                with open(lock_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 9)
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                st.toast("Ingestion halted.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to stop: {e}")
    else:
        if total > refreshed:
            st.warning(f"⏸️ Ingestion Paused ({refreshed}/{total})")
        else:
            st.success("✅ Database up to date")

# (Removed global call to ingestion_status_bar)


def load_data():
    candidates = db.get_all_candidates()
    df = pd.DataFrame(candidates)
    if not df.empty:
        # Pre-coerce numeric columns to handle "DATA NOT FOUND" strings safely
        numeric_cols = [
            'market_cap', 'float_shares', 'shares_outstanding', 'revenue_growth', 'profit_margins', 
            'gross_margins', 'operating_margins', 'return_on_equity', 
            'total_debt', 'debt_to_equity', 'free_cashflow', 'enterprise_value', 
            'ebitda', 'operating_cash_flow', 'composite_score', 'inorganic_growth_ratio'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        if 'is_acquirer' in df.columns:
            df['is_acquirer'] = df['is_acquirer'].fillna(0).astype(bool)
        if 'shares_outstanding_cagr' in df.columns:
            df['shares_outstanding_cagr'] = pd.to_numeric(df['shares_outstanding_cagr'], errors='coerce').fillna(0)
        if 'acquirer_type' in df.columns:
            df['acquirer_type'] = df['acquirer_type'].fillna('None')

        # Calculate Float % for the tables
        if 'float_shares' in df.columns and 'shares_outstanding' in df.columns:
            df['float_pct'] = (df['float_shares'] / df['shares_outstanding'].replace(0, np.nan))
                
        if 'composite_score' in df.columns:
            df['composite_score'] = df['composite_score'].fillna(-99.0)
            df = df.sort_values(by='composite_score', ascending=False)
            
    return df

def render_markdown_analysis(ticker: str):
    company_dir = os.path.join(COMPANIES_DIR, ticker)
    md_path_lite = os.path.join(company_dir, "Analysis_Lite.md")
    md_path_deep = os.path.join(company_dir, "Analysis.md")
    md_path_deep = os.path.join(company_dir, "Analysis.md")
    
    interim_mds = []
    if os.path.exists(company_dir):
        interim_mds = sorted([f for f in os.listdir(company_dir) if f.startswith("Analysis_Interim_") and f.endswith(".md")], reverse=True)
    
    has_lite = os.path.exists(md_path_lite)
    has_deep = os.path.exists(md_path_deep)
    
    if not has_lite and not has_deep and not interim_mds:
        st.warning(f"No analysis found for {ticker}.")
        return

    tabs_to_create = []
    if has_deep: tabs_to_create.append("🚀 Rocket Fuel (Deep Dive)")
    for imd in interim_mds:
        name = imd.replace("Analysis_Interim_", "").replace(".pdf.md", ".pdf").replace(".md", "")
        tabs_to_create.append(f"📅 Sell Signal: {name}")
    if has_lite: tabs_to_create.append("🌐 Search & Metrics (Lite)")
    
    tabs = st.tabs(tabs_to_create)
    
    tab_idx = 0
    if has_deep:
        with tabs[tab_idx]:
            with open(md_path_deep, "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("$", r"\$")
                st.markdown(content)
        tab_idx += 1
        
        
    for imd in interim_mds:
        with tabs[tab_idx]:
            md_path = os.path.join(company_dir, imd)
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("$", r"\$")
                st.markdown(content)
        tab_idx += 1
        
    if has_lite:
        with tabs[tab_idx]:
            with open(md_path_lite, "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("$", r"\$")
                st.markdown(content)
        tab_idx += 1

def run_analysis(ticker: str, lite_mode: bool = False, custom_question: str = None, quarterly_mode: bool = False, quarterly_pdf_path: str = None):


    if quarterly_mode:
        mode_label = f"Quarterly Sell Signal Update using {os.path.basename(quarterly_pdf_path)}"
    else:
        mode_label = "Lite Search" if lite_mode else "Rocket Fuel PDF"
        
    with st.spinner(f"Running '{mode_label}' Deep Dive for {ticker}... (This takes about 60 seconds)"):
        analyze_reports.process_target_stock(ticker, lite_mode=lite_mode, custom_question=custom_question, quarterly_mode=quarterly_mode, quarterly_pdf_path=quarterly_pdf_path, gemini_client=gemini)
    st.success("Analysis Complete!")
    st.rerun()

st.sidebar.title("10-Bagger Navigation")
view = st.sidebar.radio("Go to", ["The Launchpad", "🏆 Global Mathematical Ranking", "🛩️ The Cockpit"])

if view == "The Launchpad":
    st.title("🚀 The Quantitative Launchpad")
    ingestion_status_bar()
    st.markdown("Stocks passing the strict Tier 1 filter (<$1B Cap, <25M Float, >60% Margins, +OCF).")
    
    df = load_data()
    if not df.empty:
        # Display nicely formatting table
        cols_to_show = ['ticker', 'manual_note', 'name', 'market_cap', 'float_pct', 'revenue_growth', 'gross_margins', 'operating_cash_flow', 'recommendation']
        st.dataframe(df[cols_to_show].style.format({
            "market_cap": "${:,.0f}",
            "float_pct": "{:.1%}",
            "revenue_growth": "{:.1%}",
            "gross_margins": "{:.1%}",
            "operating_cash_flow": "${:,.0f}"
        }))
    else:
        st.info("No candidates found in the database. Run the pipeline first.")

elif view == "🛩️ The Cockpit":
    st.title("🛩️ The Cockpit (Deep Dive)")
    
    df = load_data()
    if df.empty:
        st.info("No data available.")
        st.stop()
        
    def format_ticker_option(ticker_str):
        ticker_data = df[df['ticker'] == ticker_str]
        if not ticker_data.empty:
            row = ticker_data.iloc[0]
            note = row.get('manual_note', '')
            tier = row.get('mathematical_tier', '')
            
            label = ticker_str
            if tier:
                tier_emoji = tier.split(' ')[0]
                label = f"{tier_emoji} {label}"
            if note:
                note_emoji = note.split(' ')[0]
                label = f"{label} {note_emoji}"
            if row.get('is_acquirer'):
                acquirer_type = row.get('acquirer_type', 'None')
                if acquirer_type == 'Compounder':
                    label = f"{label} 📈"
                elif acquirer_type == 'Dilutive':
                    label = f"{label} ⚠️"
                else: 
                    label = f"{label} 🛒"
            elif row.get('inorganic_growth_ratio') is not None and row.get('inorganic_growth_ratio') != 'DATA NOT FOUND':
                # M&A pipeline ran and found no acquisitions - confirmed organic
                label = f"{label} 🌱"
            return label
        return ticker_str

    tickers = df['ticker'].dropna().unique()
    
    # --- Japanese Company Filter ---
    st.sidebar.markdown("---")
    show_only_jp = st.sidebar.checkbox("🇯🇵 Show Only Japanese Companies", value=False)
    if show_only_jp:
        df = df[df['ticker'].str.contains('.T', na=False)]
        tickers = df['ticker'].dropna().unique()

    if 'selected_ticker' not in st.session_state or st.session_state.selected_ticker not in tickers:
        st.session_state.selected_ticker = tickers[0] if len(tickers) > 0 else None
        
    try:
        default_index = list(tickers).index(st.session_state.selected_ticker)
    except ValueError:
        default_index = 0

    col_prev, col_sel, col_next = st.columns([1, 4, 1])
    
    with col_prev:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Previous", use_container_width=True):
            new_idx = (default_index - 1) % len(tickers)
            st.session_state.selected_ticker = tickers[new_idx]
            st.rerun()

    with col_sel:
        selected_ticker = st.selectbox(
            "Select Candidate for Deep Dive:", 
            tickers,
            index=default_index,
            format_func=format_ticker_option
        )
        
    with col_next:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Next ➡️", use_container_width=True):
            new_idx = (default_index + 1) % len(tickers)
            st.session_state.selected_ticker = tickers[new_idx]
            st.rerun()
    
    if selected_ticker != st.session_state.selected_ticker:
        st.session_state.selected_ticker = selected_ticker
        st.rerun()
    
    with st.expander("📖 How to read the dropdown labels"):
        st.markdown("""
| Emoji | What it is | Meaning |
|:---:|:---|:---|
| 🏆 🥇 🥈 🥉 📉 | **Tier (left)** | Mathematical ranking: S / A / B / C / Avoid |
| 🟢 🟡 🔴 | **Your Note (right)** | Your personal verdict: Good / Maybe / Bad |
| 📈 | **M&A: Compounder** | Company makes acquisitions, and they grow EPS accretively (disciplined buyer) |
| ⚠️ | **M&A: Dilutive** | Company makes acquisitions, but they dilute EPS or erode margins (bad buyer) |
| 🛒 | **M&A: Heavy buyer** | Active acquirer, but acquisition quality is not yet confirmed |
| *(no M&A emoji)* | **No M&A data** | M&A analysis has not run yet, or no significant acquisition history was detected |
| 🌱 | **Confirmed Organic** | M&A pipeline ran and found no acquisition activity — growth is self-generated |
        """)

    if selected_ticker:
        stock = db.get_stock(selected_ticker)
        company_dir = os.path.join(COMPANIES_DIR, selected_ticker)
        os.makedirs(company_dir, exist_ok=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Candidate Overview")
            
            note_options = ["", "🔴 Bad", "🟡 Maybe", "🟢 Good"]
            current_note = stock.get('manual_note', "")
            if current_note not in note_options: current_note = ""
                
            selected_note = st.selectbox("My Verdict:", options=note_options, index=note_options.index(current_note), key=f"note_{selected_ticker}")
            
            if selected_note != current_note:
                db.update_manual_note(stock['isin'], selected_note)
                st.toast("Note saved!")
                st.rerun()
                
            st.markdown("---")
            st.metric("Market Cap", f"${stock.get('market_cap', 0):,.0f}")
            
            # Calculate Float Shares %
            float_shares = stock.get('float_shares', 0)
            shares_out = stock.get('shares_outstanding', 0)
            
            if shares_out and shares_out > 0:
                float_pct = (float_shares / shares_out) * 100
                st.metric("Float Shares %", f"{float_pct:.1f}%", help=f"Absolute float: {float_shares:,.0f} shares")
            else:
                st.metric("Float Shares %", "N/A", help=f"Refresh metrics to calculate percentage. Current float: {float_shares:,.0f}" if float_shares else "No float data found.")
                
            st.metric("Gross Margin", f"{stock.get('gross_margins', 0)*100:.1f}%" if stock.get('gross_margins') else "N/A")
            
                
            try:
                margin_trajectory = float(stock.get('ebitda_margin_expansion', 0.0))
                if pd.isna(margin_trajectory): margin_trajectory = 0.0
            except (ValueError, TypeError):
                margin_trajectory = 0.0
            
            try:
                ebitda_val = float(stock.get('ebitda', 0.0))
                if pd.isna(ebitda_val): ebitda_val = 0.0
            except (ValueError, TypeError):
                ebitda_val = 0.0
                
            try:
                debt_val = float(stock.get('total_debt', 0.0))
                if pd.isna(debt_val): debt_val = 0.0
            except (ValueError, TypeError):
                debt_val = 0.0

            if ebitda_val > 0:
                debt_to_ebitda = (debt_val / ebitda_val)
            else:
                debt_to_ebitda = 999.0 if debt_val > 0 else 0.0

            def render_custom_metric(label, value, color_hex, help_text):
                """Renders a premium colored metric without bulky badges."""
                # Clean help text for HTML attribute (no newlines)
                safe_help = help_text.replace('\n', ' | ').replace('"', '&quot;')
                st.markdown(f"""
                <div style="margin-bottom: 12px; cursor: help;" title="{safe_help}">
                    <div style="font-size: 0.85rem; color: #999; margin-bottom: 2px; font-weight: 500;">{label}</div>
                    <div style="font-size: 1.7rem; font-weight: 700; color: {color_hex}; line-height: 1.1;">{value}</div>
                </div>
                """, unsafe_allow_html=True)

            # --- Primary Quantitative Indicators ---
            q_col1, q_col2 = st.columns(2)
            with q_col1:
                # 1. Dilution Indicator
                try:
                    shares_cagr = float(stock.get('shares_outstanding_cagr', 0.0))
                except (ValueError, TypeError):
                    shares_cagr = 0.0
                
                dilution_help = "Year-over-year change in shares outstanding. Positive is dilution (bad), negative is buyback (good)."
                dilution_color = "#757575"
                if shares_cagr > 0.001: dilution_color = "#d32f2f" # Red for Dilution
                elif shares_cagr < -0.001: dilution_color = "#00c853" # Green for Buybacks
                
                render_custom_metric("Dilution", f"{shares_cagr*100:+.1f}%", dilution_color, dilution_help)
            
            with q_col2:
                # 2. M&A Top-Level Metric (Conditional)
                if stock.get('is_acquirer'):
                    ma_help = 'ℹ️ Methodology & Accuracy: This "Inorganic Growth Ratio" is a mechanical estimation. It triangulates 3-year average cash outflows with structural jumps in Balance Sheet Goodwill. It is designed for high-accuracy screening but is not a substitute for a manual audit of annual reports.'
                    render_custom_metric("Inorganic Growth", f"{stock.get('inorganic_growth_ratio', 0)*100:.1f}%", "#757575", ma_help)

            # 2. The Quantitative Engine (Universal)
            with st.expander("🛠️ The Quantitative Engine (Ranking Factors)", expanded=False):
                st.info("These are the raw inputs used for the Global Mathematical Ranking.")
                qcol1, qcol2 = st.columns(2)
                
                with qcol1:
                    # ROIIC
                    roiic = stock.get('roiic')
                    roi_val = float(roiic) if roiic is not None and roiic != "DATA NOT FOUND" else None
                    roi_color = "#757575"
                    if roi_val is not None:
                        if roi_val > 0.30: roi_color = "#00c853" # Elite Neon Green
                        elif roi_val > 0.15: roi_color = "#2e7d32" # Good Forest Green
                        elif roi_val > 0.05: roi_color = "#757575" # Mid
                        else: roi_color = "#d32f2f" # Bad
                    
                    roiic_help = "ROIIC: Efficiency of new capital. (Elite: >30%, Good: >15%, Mid: >5%, Bad: <5%)"
                    render_custom_metric("ROIIC", f"{roi_val*100:.1f}%" if roi_val is not None else "N/A", roi_color, roiic_help)
                    
                    # 3GP Score
                    tgp = stock.get('three_gp_score')
                    tgp_val = float(tgp) if tgp is not None and tgp != "DATA NOT FOUND" else None
                    tgp_color = "#757575"
                    if tgp_val is not None:
                        if tgp_val > 80: tgp_color = "#00c853" # Elite
                        elif tgp_val > 50: tgp_color = "#2e7d32" # Good
                        elif tgp_val > 20: tgp_color = "#757575" # Mid
                        else: tgp_color = "#d32f2f" # Bad
                    
                    three_gp_help = "3GP: 3x Rev Growth + EBITDA Margin. (Elite: >80, Good: >50, Mid: >20, Bad: <20)"
                    render_custom_metric("3GP Score", f"{tgp_val:.1f}" if tgp_val is not None else "N/A", tgp_color, three_gp_help)
                    
                    # Altman Z
                    zsc = stock.get('altman_z_score')
                    z_val = float(zsc) if zsc is not None and zsc != "DATA NOT FOUND" else None
                    z_color = "#757575"
                    if z_val is not None:
                        if z_val > 3.0: z_color = "#00c853" # Safe/Elite
                        elif z_val > 1.8: z_color = "#757575" # Grey
                        else: z_color = "#d32f2f" # Distressed
                    
                    altman_help = "Altman Z: Bankruptcy risk. (Safe: >3.0, Grey: >1.8, Alarm: <1.8)"
                    render_custom_metric("Altman Z-Score", f"{z_val:.2f}" if z_val is not None else "N/A", z_color, altman_help)

                with qcol2:
                    # Accruals Ratio
                    acc = stock.get('accruals_ratio')
                    acc_val = float(acc) if acc is not None and acc != "DATA NOT FOUND" else None
                    acc_color = "#757575"
                    if acc_val is not None:
                        if acc_val < -0.10: acc_color = "#00c853" # Elite
                        elif acc_val < 0.10: acc_color = "#757575" # Good/Stable
                        else: acc_color = "#d32f2f" # Bad
                    
                    accruals_help = "Accruals: Quality of earnings/Cash conversion. (Elite: < -0.10, Good: < 0.10, Bad: > 0.10)"
                    render_custom_metric("Accruals Ratio", f"{acc_val:.3f}" if acc_val is not None else "N/A", acc_color, accruals_help)
                    
                    # Cash Runway
                    runway = stock.get('cash_runway_months')
                    runway_val = float(runway) if runway is not None and runway != "DATA NOT FOUND" else None
                    runway_str, runway_color = ("N/A", "#757575")
                    if runway_val is not None:
                        if runway_val == 999.0:
                            runway_str, runway_color = ("∞", "#00c853") # Elite
                        else:
                            runway_str = f"{runway_val:.0f} mo"
                            if runway_val > 24: runway_color = "#2e7d32" # Good
                            elif runway_val > 12: runway_color = "#757575"
                            else: runway_color = "#d32f2f"
                    
                    runway_help = "Runway: Months of cash left at current burn. (Elite: ∞, Good: >24 mo, Mid: >12 mo, Bad: <12 mo)"
                    render_custom_metric("Cash Runway", runway_str, runway_color, runway_help)
                    
                    # Proxy WACC
                    wac = stock.get('proxy_wacc')
                    wac_val = float(wac) if wac is not None and wac != "DATA NOT FOUND" else None
                    wac_color = "#757575"
                    if wac_val is not None:
                        if wac_val <= 0.085: wac_color = "#00c853" # Elite Safe
                        elif wac_val <= 0.11: wac_color = "#757575" # Standard
                        else: wac_color = "#d32f2f" # High Risk
                    
                    wacc_help = "WACC: Est. cost of capital based on z-score. (Safe: 8.5%, Risk: 15%)"
                    render_custom_metric("Proxy WACC", f"{wac_val*100:.1f}%" if wac_val is not None else "N/A", wac_color, wacc_help)

            # 3. M&A Assessment (Conditional)
            if stock.get('is_acquirer'):
                acquirer_type = stock.get('acquirer_type', 'None')
                badge = "M&A Compounder 📈" if acquirer_type == "Compounder" else ("M&A Diluter ⚠️" if acquirer_type == "Dilutive" else "M&A Heavy 🛒")
                with st.expander("📝 M&A Strategy Assessment"):
                    st.markdown(f"**Verdict:** {badge}")
                    if acquirer_type == "Compounder":
                        st.success("This company is executing a successful Roll-up strategy. They are not mathematically penalized.")
                    elif acquirer_type == "Dilutive":
                        st.error("This company is executing a poor Roll-up strategy. Their revenue growth has been mathematically discounted in the rankings.")
                    
                    st.markdown(f"""
                    *   **Funding (Share Count):** The share count has **{'shrunk' if shares_cagr < -0.001 else 'grown'}** by **{abs(shares_cagr*100):.1f}%** annually. {'🟢 (Accretive — Buybacks)' if shares_cagr < -0.001 else '🔵 (Neutral — Stable)' if shares_cagr <= 0.01 else '🟡 (Mild Dilution)' if shares_cagr <= 0.03 else '🔴 (Dilutive)'}
                    *   **Execution (Margins):** EBITDA margins have **{'expanded' if margin_trajectory >= 0 else 'contracted'}** by **{abs(margin_trajectory*100):.1f} pts**. {'(Successful Integration)' if margin_trajectory >= 0 else '(Diworsification)' if margin_trajectory < -0.05 else '(Mild Compression)'}
                    
                                       """)
            
            # 4. Risk & Solvency (Universal)
            with st.expander("⚠️ Risk & Solvency"):
                is_neg_ebitda = ebitda_val <= 0
                risk_label = "🔴 High Risk (Neg EBITDA)" if is_neg_ebitda else ("🟢 Healthy" if debt_to_ebitda <= 3.0 else "🟡 Leveraged")
                st.markdown(f"**Status:** {risk_label}")
                
                runway = stock.get('cash_runway_months')
                runway_text = "N/A"
                if runway == 999.0:
                    runway_text = "∞ (Self-Sustaining)"
                elif runway is not None and runway != "DATA NOT FOUND":
                    runway_text = f"{float(runway):.0f} months"

                st.markdown(f"""
                *   **Leverage (Debt/EBITDA):** **{'N/A (Negative EBITDA)' if is_neg_ebitda else f'{debt_to_ebitda:.1f}x'}**. {'(Safe)' if debt_to_ebitda <= 4.0 else '(Over-Leveraged)' if debt_to_ebitda < 999.0 else '(Cannot calculate — EBITDA is zero or negative)'}
                *   **Liquidity:** {runway_text} of cash runway.
                """)
            
            st.markdown(f"📈 **[View on Yahoo Finance](https://finance.yahoo.com/quote/{selected_ticker})**")
            ir_query = quote_plus(f"{stock['name']} investor relations")
            st.markdown(f"🏛️ **[Investor Relations Search](https://www.google.com/search?q={ir_query})**")
            

            st.markdown("---")
            pdf_path = None
            for file in os.listdir(company_dir):
                if file.lower().endswith('.pdf') and not file.startswith('Interim_') and not file.startswith('Calendar_'):
                    pdf_path = os.path.join(company_dir, file)
                    break
            
            if st.button("🌐 Search & Analyze Metrics (Lite)", key=f"lite_{selected_ticker}"):
                run_analysis(selected_ticker, lite_mode=True)
                
            has_pdf = bool(pdf_path)
            st.markdown("### Document Status (Annual Report)")
            if has_pdf:
                st.success(f"PDF Found: `{os.path.basename(pdf_path)}`")
                if st.button("🗑️ Remove PDF", key=f"remove_pdf_{selected_ticker}"):
                    os.remove(pdf_path)
                    db.update_stock_metrics(stock['isin'], {'annual_report_path': None})
                    st.rerun()
            if not has_pdf:
                st.error("No Annual Report PDF found.")
                
                uploaded_file = st.file_uploader("Upload Annual Report PDF", type="pdf", key=f"annual_up_{selected_ticker}")
                if uploaded_file is not None:
                    pdf_save_path = os.path.join(company_dir, uploaded_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    db.update_stock_metrics(stock['isin'], {'annual_report_path': pdf_save_path})
                    st.success("Annual Report uploaded!")
                    st.rerun()

            # Japanese Company Support (Annual)
            if selected_ticker.endswith(".T"):
                with st.expander("🇯🇵 EDINET Japan (Annual Report)", expanded=not has_pdf):
                    st.info("💡 Fetch the official Annual Securities Report (Yuho) from EDINET.")
                    if st.button("🇯🇵 Download Japanese Yuho (10-K)", key=f"dl_jp_{selected_ticker}"):
                        with st.spinner("Searching EDINET... (this may take a minute)"):
                            import subprocess
                            try:
                                result = subprocess.run(
                                    [sys.executable, "pipeline/download_jp_report.py", selected_ticker, "--days", "500", "--type", "annual"],
                                    capture_output=True, text=True, check=False
                                )
                                if result.returncode == 0:
                                    st.success("Download Successful!")
                                    st.rerun()
                                else:
                                    st.error(f"Download Failed: {result.stderr or 'No recent Yuho found.'}")
                            except Exception as e:
                                st.error(f"Error: {e}")

            custom_question_annual = st.text_area("Optional: Custom Detective Question / Thesis Note", key=f"q_{selected_ticker}")
            if st.button("🚀 Run 'Rocket Fuel' Deep Dive (PDF)", disabled=not has_pdf, key=f"deep_{selected_ticker}"):
                run_analysis(selected_ticker, lite_mode=False, custom_question=custom_question_annual)

            st.markdown("### Interim / Quarterly Reports")
            
            # Japanese Company Support (Quarterly)
            if selected_ticker.endswith(".T"):
                with st.expander("🇯🇵 EDINET Japan (Quarterly/Interim)", expanded=False):
                    st.info("💡 Fetch the official Quarterly or Interim report from EDINET.")
                    if st.button("🇯🇵 Download Quarterly/Interim Report", key=f"dl_jp_qt_{selected_ticker}"):
                        with st.spinner("Searching EDINET... (this may take a minute)"):
                            import subprocess
                            try:
                                result = subprocess.run(
                                    [sys.executable, "pipeline/download_jp_report.py", selected_ticker, "--days", "300", "--type", "quarterly"],
                                    capture_output=True, text=True, check=False
                                )
                                if result.returncode == 0:
                                    st.success("Download Successful!")
                                    st.rerun()
                                else:
                                    st.error(f"Download Failed: {result.stderr or 'No recent Quarterly/Interim report found.'}")
                            except Exception as e:
                                st.error(f"Error: {e}")
            interim_pdfs = sorted([f for f in os.listdir(company_dir) if f.lower().endswith('.pdf') and f.startswith('Interim_')], reverse=True)
            if interim_pdfs:
                selected_interim = st.selectbox("Select Interim Report", interim_pdfs, key=f"interim_sel_{selected_ticker}")
                interim_path = os.path.join(company_dir, selected_interim)
                md_path = os.path.join(company_dir, f"Analysis_{selected_interim}.md")
                if not os.path.exists(md_path):
                    custom_question_interim = st.text_area("Specific things to check?", key=f"q_int_{selected_ticker}")
                    if st.button(f"📅 Run Sell Signal Analysis on {selected_interim}"):
                        run_analysis(selected_ticker, quarterly_mode=True, quarterly_pdf_path=interim_path, custom_question=custom_question_interim)
            
            uploaded_interim = st.file_uploader("Upload Interim/Quarterly PDF", type="pdf", key=f"interim_up_{selected_ticker}")
            if uploaded_interim is not None:
                interim_save_path = os.path.join(company_dir, f"Interim_{uploaded_interim.name}")
                with open(interim_save_path, "wb") as f:
                    f.write(uploaded_interim.getbuffer())
                st.rerun()

        with col2:
            st.subheader("AI Investment Thesis")
            render_markdown_analysis(selected_ticker)

elif view == "🏆 Global Mathematical Ranking":
    st.title("🏆 Global Mathematical Ranking")
    st.markdown("Hierarchical ranking of the entire candidate universe, calculated mathematically using *The Calculus of Outperformance*.")
    
    with st.expander("ℹ️ How are these rankings calculated? (Methodology)"):
        st.markdown("""
        ### The Calculus of Outperformance
        This model uses a **Multi-Factor Weighted Z-Score** to rank companies against their peers. Instead of absolute values, we measure how many *Standard Deviations* a company is from the average.
        
        **1. Capital Efficiency (30%)**
        - **ROIIC**: Return on Incremental Invested Capital. Measures how much profit is generated for every Euro of new capital deployed.
        - **3GP Score**: Measures gross profit relative to total assets.
        
        **2. Growth & Valuation (30%)**
        - **Revenue Growth**: Pure top-line expansion.
        - **Size Factor**: Logarithmic Market Cap. Smaller companies get a statistical "boost" due to higher growth ceiling.
        
        **3. Moat & Margin Durability (25%)**
        - **EBITDA Expansion**: Trailing margin improvement.
        - **ROIC Stability**: Low decay in returns on capital.
        
        **4. Downside & Forensic Risk (15%)**
        - **Altman Z-Score**: Probability of bankruptcy (Higher is better).
        - **Accruals Ratio**: Quality of earnings (Lower is better).
        
        ---
        ⚠️ **Note on "Anomalies":** 
        Because the model is **Additive**, a world-class score in one dimension (like a massive ROIIC jump) can push a company to the top even if other factors are average. 
        *Example:* High ROIIC on low revenue growth often indicates **Operating Leverage** (cyclical recovery) rather than **Reinvestment Growth**. Use the *Cockpit* to verify the qualitative thesis!
        """)

    from core.config import DATA_DIR
    tier_list_path = os.path.join(DATA_DIR, "findings", "TIER_LIST_RANKING_MATH.md")
    
    if os.path.exists(tier_list_path):
        with open(tier_list_path, "r", encoding="utf-8") as f:
            content = f.read().replace("$", r"\$")
            st.markdown(content)
        
        if st.button("🔄 Regenerate Global Mathematical Rankings", key="regen_tl"):
            with st.spinner("Calculating Rankings..."):
                rank_candidates.process_tier_list(gemini_client=gemini)
            st.rerun()
    else:
        st.info("No Global Ranking generated yet.")
        if st.button("🚀 Generate Global Mathematical Rankings", key="gen_tl"):
            with st.spinner("Calculating Rankings..."):
                rank_candidates.process_tier_list(gemini_client=gemini)
            st.rerun()
