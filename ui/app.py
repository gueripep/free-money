import os
import streamlit as st
import pandas as pd
import yfinance as yf
from urllib.parse import quote_plus

# Ensure Streamlit runs with the correct path relative to the root
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.database as db
from core.config import COMPANIES_DIR
import importlib.util

spec = importlib.util.spec_from_file_location("analyze_reports", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline", "03_analyze_reports.py"))
analyze_reports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze_reports)

def load_data():
    candidates = db.get_launchpad_candidates(100)
    return pd.DataFrame(candidates)

def render_markdown_analysis(ticker: str):
    company_dir = os.path.join(COMPANIES_DIR, ticker)
    md_path_lite = os.path.join(company_dir, "Analysis_Lite.md")
    md_path_deep = os.path.join(company_dir, "Analysis.md")
    
    has_lite = os.path.exists(md_path_lite)
    has_deep = os.path.exists(md_path_deep)
    
    if not has_lite and not has_deep:
        st.warning(f"No analysis found for {ticker}.")
        return

    tabs_to_create = []
    if has_deep: tabs_to_create.append("🚀 Rocket Fuel (Deep Dive)")
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
        
    if has_lite:
        with tabs[tab_idx]:
            with open(md_path_lite, "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("$", r"\$")
                st.markdown(content)
        tab_idx += 1

def run_analysis(ticker: str, lite_mode: bool = False, custom_question: str = None):
    mode_label = "Lite Search" if lite_mode else "Rocket Fuel PDF"
    with st.spinner(f"Running '{mode_label}' Deep Dive for {ticker}... (This takes about 60 seconds)"):
        analyze_reports.process_target_stock(ticker, lite_mode=lite_mode, custom_question=custom_question)
    st.success("Analysis Complete!")
    st.rerun()

st.set_page_config(page_title="Architecture of Exponential Returns", layout="wide")

st.sidebar.title("10-Bagger Navigation")
view = st.sidebar.radio("Go to", ["The Launchpad", "The Cockpit"])

if view == "The Launchpad":
    st.title("🚀 The Quantitative Launchpad")
    st.markdown("Stocks passing the strict Tier 1 filter (<$1B Cap, <25M Float, >60% Margins, +OCF).")
    
    df = load_data()
    if not df.empty:
        # Display nicely formatting table
        cols_to_show = ['ticker', 'manual_note', 'name', 'market_cap', 'float_shares', 'revenue_growth', 'gross_margins', 'operating_cash_flow', 'recommendation']
        st.dataframe(df[cols_to_show].style.format({
            "market_cap": "${:,.0f}",
            "float_shares": "{:,.0f}",
            "revenue_growth": "{:.1%}",
            "gross_margins": "{:.1%}",
            "operating_cash_flow": "${:,.0f}"
        }))
    else:
        st.info("No candidates found in the database. Run the pipeline first.")

elif view == "The Cockpit":
    st.title("🛩️ The Cockpit (Deep Dive)")
    
    df = load_data()
    if df.empty:
        st.info("No data available.")
        st.stop()
        
    def format_ticker_option(ticker_str):
        # We need to find the note for this ticker
        ticker_data = df[df['ticker'] == ticker_str]
        if not ticker_data.empty:
            note = ticker_data.iloc[0].get('manual_note', '')
            if note:
                # Extract just the emoji for a cleaner dropdown
                emoji = note.split(' ')[0] 
                return f"{emoji} {ticker_str}"
        return ticker_str

    tickers = df['ticker'].dropna().unique()
    
    # Initialize session state for the selected ticker if it doesn't exist
    if 'selected_ticker' not in st.session_state:
        st.session_state.selected_ticker = tickers[0] if len(tickers) > 0 else None
        
    # Helper index finder
    try:
        default_index = list(tickers).index(st.session_state.selected_ticker)
    except ValueError:
        default_index = 0

    selected_ticker = st.selectbox(
        "Select Candidate for Deep Dive:", 
        tickers,
        index=default_index,
        format_func=format_ticker_option
    )
    
    # Update session state if user manually changes the dropdown
    if selected_ticker != st.session_state.selected_ticker:
        st.session_state.selected_ticker = selected_ticker
    
    if selected_ticker:
        stock = db.get_stock(selected_ticker)
        company_dir = os.path.join(COMPANIES_DIR, selected_ticker)
        os.makedirs(company_dir, exist_ok=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Candidate Overview")
            
            # Manual Note Logic
            note_options = ["", "🔴 Bad", "🟡 Maybe", "🟢 Good"]
            current_note = stock.get('manual_note', "")
            
            # Ensure current note is in options, even if it's legacy data
            if current_note not in note_options:
                current_note = ""
                
            selected_note = st.selectbox(
                "My Verdict:", 
                options=note_options, 
                index=note_options.index(current_note),
                key=f"note_{selected_ticker}"
            )
            
            if selected_note != current_note:
                db.update_manual_note(stock['isin'], selected_note)
                st.toast("Note saved!")
                st.rerun()
                
            st.markdown("---")
            st.metric("Market Cap", f"${stock.get('market_cap', 0):,.0f}")
            st.metric("Float Shares", f"{stock.get('float_shares', 0):,.0f}")
            st.metric("Gross Margin", f"{stock.get('gross_margins', 0)*100:.1f}%" if stock.get('gross_margins') else "N/A")
            
            st.markdown(f"📈 **[View on Yahoo Finance](https://finance.yahoo.com/quote/{selected_ticker})**")
            
            # Check for PDF
            pdf_path = None
            for file in os.listdir(company_dir):
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(company_dir, file)
                    break
            
            st.markdown("### AI Analysis Actions")
            custom_question = st.text_area("Optional: Custom Detective Question / Thesis Note", help="Ask the AI to investigate something specific (e.g., 'Why is EV/EBITDA only 3.3x?')", key=f"q_{selected_ticker}")
            
            if st.button("🌐 Search & Analyze Metrics (Lite)", help="Runs a cheaper, faster analysis using basic metrics without needing a PDF."):
                run_analysis(selected_ticker, lite_mode=True, custom_question=custom_question)
                
            has_pdf = bool(pdf_path)
            if st.button("🚀 Run 'Rocket Fuel' Deep Dive (PDF)", disabled=not has_pdf, help="Requires an uploaded Annual Report PDF. Fully analyzes the actual document."):
                run_analysis(selected_ticker, lite_mode=False, custom_question=custom_question)
            
            st.markdown("---")
            st.markdown("### Document Status")
            if has_pdf:
                st.success(f"PDF Found: `{os.path.basename(pdf_path)}`")
            else:
                st.error("No Annual Report PDF found. Upload one to unlock the Rocket Fuel analysis.")
                st.markdown("**Optional:**")
                search_query = quote_plus(f"{stock['name']} {selected_ticker} Document d'enregistrement universel 2024 pdf")
                st.markdown(f"1. [Search Google for Report](https://www.google.com/search?q={search_query})")
                
                uploaded_file = st.file_uploader("2. Upload PDF Report", type="pdf")
                if uploaded_file is not None:
                    # Save the file
                    pdf_save_path = os.path.join(company_dir, uploaded_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Update DB
                    db.update_stock_metrics(stock['isin'], {'annual_report_path': pdf_save_path})
                    st.success("File uploaded successfully!")
                    st.rerun()

        with col2:
            st.subheader("AI Investment Thesis")
            render_markdown_analysis(selected_ticker)
