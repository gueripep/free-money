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
        analyze_reports.process_target_stock(ticker, lite_mode=lite_mode, custom_question=custom_question, quarterly_mode=quarterly_mode, quarterly_pdf_path=quarterly_pdf_path)
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

    col_prev, col_sel, col_next = st.columns([1, 4, 1])
    
    with col_prev:
        st.markdown("<br>", unsafe_allow_html=True) # spacing alignment
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
        st.markdown("<br>", unsafe_allow_html=True) # spacing alignment
        if st.button("Next ➡️", use_container_width=True):
            new_idx = (default_index + 1) % len(tickers)
            st.session_state.selected_ticker = tickers[new_idx]
            st.rerun()
    
    # Update session state if user manually changes the dropdown
    if selected_ticker != st.session_state.selected_ticker:
        st.session_state.selected_ticker = selected_ticker
        st.rerun()
    
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
            ir_query = quote_plus(f"{stock['name']} investor relations")
            st.markdown(f"🏛️ **[Investor Relations Search](https://www.google.com/search?q={ir_query})**")
            
            # Check for PDF
            pdf_path = None
            for file in os.listdir(company_dir):
                if file.lower().endswith('.pdf') and not file.startswith('Interim_'):
                    pdf_path = os.path.join(company_dir, file)
                    break
            
            if st.button("🌐 Search & Analyze Metrics (Lite)", help="Runs a cheaper, faster analysis using basic metrics without needing a PDF."):
                run_analysis(selected_ticker, lite_mode=True)
                
            has_pdf = bool(pdf_path)
            
            st.markdown("---")
            st.markdown("### Document Status (Annual Report)")
            if has_pdf:
                st.success(f"PDF Found: `{os.path.basename(pdf_path)}`")
                if st.button("🗑️ Remove PDF", key=f"remove_pdf_{selected_ticker}"):
                    try:
                        os.remove(pdf_path)
                        db.update_stock_metrics(stock['isin'], {'annual_report_path': None})
                        st.toast("Annual Report PDF removed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to remove PDF: {e}")
            else:
                st.error("No Annual Report PDF found. Upload one to unlock the Rocket Fuel analysis.")
                
                uploaded_file = st.file_uploader("Upload Annual Report PDF", type="pdf", key=f"annual_up_{selected_ticker}")
                if uploaded_file is not None:
                    # Save the file
                    pdf_save_path = os.path.join(company_dir, uploaded_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Update DB
                    db.update_stock_metrics(stock['isin'], {'annual_report_path': pdf_save_path})
                    st.success("Annual Report uploaded successfully!")
                    st.rerun()

            custom_question_annual = st.text_area("Optional: Custom Detective Question / Thesis Note", help="Ask the AI to investigate something specific in the Annual Report (e.g., 'Why is EV/EBITDA only 3.3x?')", key=f"q_{selected_ticker}")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Run 'Rocket Fuel' Deep Dive (PDF)", disabled=not has_pdf, help="Requires an uploaded Annual Report PDF. Fully analyzes the actual document."):
                run_analysis(selected_ticker, lite_mode=False, custom_question=custom_question_annual)

            st.markdown("### Interim / Quarterly Reports")
            interim_pdfs = sorted([f for f in os.listdir(company_dir) if f.lower().endswith('.pdf') and f.startswith('Interim_')], reverse=True)
            
            if interim_pdfs:
                selected_interim = st.selectbox("Select Interim Report", interim_pdfs, key=f"interim_sel_{selected_ticker}")
                interim_path = os.path.join(company_dir, selected_interim)
                md_name = f"Analysis_{selected_interim}.md"
                md_path = os.path.join(company_dir, md_name)
                
                if not os.path.exists(md_path):
                    custom_question_interim = st.text_area("Optional: Specific things to check in this report?", key=f"q_int_{selected_ticker}")
                    if st.button(f"📅 Run Sell Signal Analysis on {selected_interim}"):
                        run_analysis(selected_ticker, quarterly_mode=True, quarterly_pdf_path=interim_path, custom_question=custom_question_interim)
                else:
                    st.success(f"Analysis already exists for `{selected_interim}`. View in tabs.")
            else:
                st.info("No interim reports found.")
                
            uploaded_interim = st.file_uploader("Upload Interim/Quarterly Report PDF", type="pdf", key=f"interim_up_{selected_ticker}")
            if uploaded_interim is not None:
                interim_save_path = os.path.join(company_dir, f"Interim_{uploaded_interim.name}")
                with open(interim_save_path, "wb") as f:
                    f.write(uploaded_interim.getbuffer())
                st.success("Interim Report uploaded successfully!")
                st.rerun()

        with col2:
            st.subheader("AI Investment Thesis")
            render_markdown_analysis(selected_ticker)
