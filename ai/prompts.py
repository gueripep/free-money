import datetime

def get_lite_analysis_prompt(stock: dict, custom_question: str = None) -> str:
    """A lighter, search-based prompt that focuses on Google Search extraction."""
    
    current_date = datetime.datetime.now().strftime('%B %d, %Y')
    custom_directive = f"\n\nUSER'S CUSTOM INVESTIGATION DIRECTIVE:\n{custom_question}\nYou MUST weave the answers to these specific questions naturally into the relevant sections of your analysis (e.g., Business Summary, Unknowns, etc.). Do not just list them at the end.\n" if custom_question else ""
    
    return f"""
Act as a forensic equity analyst. You are evaluating this stock based on its basic financial metrics and what you can infer about its qualitative story.

TARGET: {stock['name']} ({stock.get('ticker', stock['isin'])})
CURRENT DATE: {current_date}

METRICS CONTEXT (The Quantitative Launchpad):
- Market Cap: {stock.get('market_cap', 'N/A')} (Check: Is it in the $50M-$1B sweet spot?)
- Float: {stock.get('float_shares', 'N/A')} (Check: Is it < 25M?)
- Gross Margin: {stock.get('gross_margins', 'N/A')} (Check: Is it > 60%?)
- Operating Cash Flow: {stock.get('operating_cash_flow', 'N/A')} (Check: Is it self-funding?)

VALUATION CONTEXT (Live from Yahoo Finance):
**CRITICAL INSTRUCTION: You MUST use the live metrics below as the single source of truth for the company's CURRENT valuation and pricing.**
- Trailing P/E: {stock.get('trailing_pe', 'N/A')}
- Forward P/E: {stock.get('forward_pe', 'N/A')}
- EV/EBITDA: {stock.get('ev_to_ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}{custom_directive}

OBJECTIVE:
Provide a preliminary "Lite" thesis. Because you do not have the full Annual Report PDF, focus heavily on the financial physics (margins, cash flow) and any known qualitative facts about this industry.

OUTPUT FORMAT (JSON ONLY):
{{
    "recommendation": "Buy / Watch / Avoid",
    "conviction_score": (1-10, be strict),
    "is_10_bagger_candidate": true/false,
    "analysis": {{
        "business_summary": "What does this company do? Explain clearly.",
        "metrics_evaluation": "Is it financially healthy based on the numbers? Specifically evaluate the debt load and solvency if data is available.",
        "valuation": "Compare the business quality against the current valuation multiples.",
        "initial_gut_check": "Does it look like a potential multi-bagger, or is the business model inherently too capital intensive (e.g., Banks, REITs)?",
        "unknowns": "What are the biggest questions the Annual Report needs to answer?"
    }},
    "verdict_summary": "[LITE SEARCH ANALYSIS] A fast, preliminary executive summary based on metrics."
}}
"""

def get_exponential_returns_prompt(stock: dict, doc_names: list, custom_question: str = None, doc_age_months: int = None) -> str:
    """Returns the 'Architecture of Exponential Returns' prompt for PDF Deep Dives."""
    
    current_date = datetime.datetime.now().strftime('%B %d, %Y')
    age_context = f"\nDOCUMENT AGE: The provided Annual Report is approximately {doc_age_months} months old. You MUST factor this time gap into your entire assessment—especially regarding cash burn, debt maturity, and market shifts." if doc_age_months is not None else ""
    
    custom_directive = f"\n\nUSER'S CUSTOM INVESTIGATION DIRECTIVE:\n{custom_question}\nYou MUST explicitly investigate these specific questions. Weave your findings and answers naturally into the relevant sections of your analysis (e.g., The Story, The Gate, Red Flags). Do not create a separate section for it.\n" if custom_question else ""
    
    return f"""
Act as a senior forensic equity analyst and disciplined contrarian investor.
You are efficiently synthesizing the "Architecture of Exponential Returns" framework (Lynch, O'Neil, Phelps, Cassel).

TARGET: {stock['name']} ({stock.get('ticker', stock['isin'])})
CURRENT DATE: {current_date}{age_context}
DOCUMENTS: {', '.join(doc_names) if doc_names else 'None'}

METRICS CONTEXT (The Quantitative Launchpad):
- Market Cap: {stock.get('market_cap', 'N/A')} (Check: Is it in the $50M-$1B sweet spot?)
- Float: {stock.get('float_shares', 'N/A')} (Check: Is it < 25M?)
- Gross Margin: {stock.get('gross_margins', 'N/A')} (Check: Is it > 60%?)
- Operating Cash Flow: {stock.get('operating_cash_flow', 'N/A')} (Check: Is it self-funding?)

VALUATION CONTEXT (Live from Yahoo Finance):
**CRITICAL INSTRUCTION: The Annual Report PDF contains HISTORICAL data. You MUST use the live metrics below as the single source of truth for the company's CURRENT valuation and pricing. Furthermore, compare the CURRENT DATE to the date of the documents to understand how old the data is.**
- Trailing P/E: {stock.get('trailing_pe', 'N/A')}
- Forward P/E: {stock.get('forward_pe', 'N/A')}
- EV/EBITDA: {stock.get('ev_to_ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}{custom_directive}

OBJECTIVE:
Conduct a brutal, evidence-based deep dive using the provided Annual Report PDF to determine if this stock has the physics to be a 10-Bagger.
You must cite specific page numbers or sections from the provided documents for every qualitative claim.

SECTION 1: THE FORENSIC LAUNCHPAD (Financial Health)
- **Capital Intensity & Scalability**: Is this business mathematically capable of exponential growth without exponential capital requirements? Evaluate if revenue growth requires massive, linear capital deployment (e.g., buying physical buildings, heavy manufacturing) versus scalable operating leverage. **CRITICAL:** If the business model is inherently capital intensive with low asset turnover (e.g., Banks, REITs), it CANNOT be a 10-bagger candidate.
- **Operating Leverage**: Analyze the cost structure.
- **Self-Funding**: Does Operating Cash Flow cover CapEx?
- **Return on Capital**: Is there evidence of high/rising ROIC?
- **Solvency & Debt**: Calculate Net Debt / EBITDA. Is it dangerously high (>3x)? What is the interest coverage ratio? Is the debt suffocating the business?

SECTION 2: THE QUALITATIVE ROCKET FUEL (The Story)
- **Lynch's "Boring" Factor**: Is the business dull or ignored?
- **Phelps's "Gate" (Moat)**: What is the specific structural competitive advantage?
- **O'Neil's "N" Factor**: What is NEW? Catalyst?
- **Cassel's "Intelligent Fanatics"**: Founder-led? Skin in the Game? Salary vs. Equity? Frugal tone?

SECTION 3: THE VALUATION CHECK
- **Pricing**: Does the current valuation (P/E, EV/EBITDA) make sense given the story and metrics? Are we buying growth at a reasonable price (GARP)?

SECTION 4: THE RED FLAG FORCE MULTIPLIER (Disqualifiers)
- **Diworsification**: Acquisitions outside core competence?
- **The "Egonomist"**: Is the CEO promotional?
- **Auditor Instability**: Any mention of auditor changes or disputes?

SECTION 5: THE PRE-MORTEM (Anti-Bias)
- Why will this investment FAIL?
- Assume the stock drops 50% next year. What was the cause?

OUTPUT FORMAT INSTRUCTIONS (JSON ONLY):
1. **Rich Markdown Required:** The strings inside the JSON values must aggressively use Markdown.
2. **Tables:** Use Markdown tables to compare metrics across different years or to list competitors/segments.
3. **Lists & Styling:** Use bolding (`**bold**`), bullet points (`-`), and blockquotes (`>`) to make the analysis highly readable and punchy.
4. **Citations:** Every qualitative claim must end with a page number citation (e.g., `(p. 42)`).

JSON STRUCTURE:
{{
    "recommendation": "Buy / Watch / Avoid",
    "conviction_score": (1-10, be strict),
    "is_10_bagger_candidate": true/false,
    "analysis": {{
        "forensic_launchpad": "Detailed analysis. **Must include a Markdown table** of key financial changes if data is available. Cite evidence.",
        "the_story": "Lynch's boring factor check. Use bullet points for key aspects.",
        "the_gate": "Deep dive into the Moat. Structure with clear sub-headings.",
        "rocket_fuel": "The Catalyst/N factor. Make it punchy.",
        "intelligent_fanatics": "Management assessment. Focus on insider ownership and compensation structure.",
        "valuation": "Compare the bull case against the current valuation multiples. Is it mispriced?",
        "red_flags": "List any red flags found using a bulleted list.",
        "pre_mortem": "The Bear Case. Bullet point the top 3 reasons this investment could fail."
    }},
    "verdict_summary": "[ROCKET FUEL PDF DEEP DIVE] A high-conviction executive summary formatted beautifully."
}}
"""
