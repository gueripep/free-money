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
- **Raw Enterprise Value (EV):** {stock.get('enterprise_value', 'N/A')}
- **Raw EBITDA:** {stock.get('ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}
- Revenue Growth: {stock.get('revenue_growth', 'N/A')}
- Profit Margins: {stock.get('profit_margins', 'N/A')} 
- Operating Margins: {stock.get('operating_margins', 'N/A')}
- Return on Equity (ROE): {stock.get('return_on_equity', 'N/A')}
- Total Debt: {stock.get('total_debt', 'N/A')}
- Debt to Equity: {stock.get('debt_to_equity', 'N/A')}
- Free Cash Flow: {stock.get('free_cashflow', 'N/A')}{custom_directive}

OBJECTIVE:
Provide a preliminary "Lite" thesis. Because you do not have the full Annual Report PDF, focus heavily on the financial physics (margins, cash flow) and any known qualitative facts about this industry. 
CRITICAL DIRECTIVE: Before analyzing the specific metrics, step back and think globally about the business. What is the fundamental problem it solves? What are the structural realities of its industry? You must take the role of an objective, forensic analyst. Identify the primary structural barrier or risk that could prevent exponential growth, but explicitly counter-weigh this against the quantitative metrics. If the business has exceptional margins, cash flow, and a low valuation, do not arbitrarily penalize it.

OUTPUT FORMAT (JSON ONLY):
{{
    "recommendation": "Buy / Watch / Avoid",
    "conviction_score": (1-10, be objective, reward strong metrics),
    "is_10_bagger_candidate": true/false,
    "global_thought": "Synthesize the overarching business reality and industry ecosystem. Clearly identify the main structural barrier to exponential growth, but remain objective about the potential upside.",
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
- **Raw Enterprise Value (EV):** {stock.get('enterprise_value', 'N/A')}
- **Raw EBITDA:** {stock.get('ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}
- Revenue Growth: {stock.get('revenue_growth', 'N/A')}
- Profit Margins: {stock.get('profit_margins', 'N/A')} 
- Operating Margins: {stock.get('operating_margins', 'N/A')}
- Return on Equity (ROE): {stock.get('return_on_equity', 'N/A')}
- Total Debt: {stock.get('total_debt', 'N/A')}
- Debt to Equity: {stock.get('debt_to_equity', 'N/A')}
- Free Cash Flow: {stock.get('free_cashflow', 'N/A')}{custom_directive}

OBJECTIVE:
Conduct a brutal, evidence-based deep dive using the provided Annual Report PDF to determine if this stock has the physics to be a 10-Bagger.
CRITICAL DIRECTIVE: First, synthesize a "Global Thought". Understand the absolute reality of this business ecosystem, secular trends, and broader market positioning BEFORE looking for the "Rocket Fuel". You must act as a disciplined, objective analyst. Identify the primary structural barriers or risks, but weigh them fairly against the quantitative metrics and the deep dive evidence. Do not auto-penalize a stock if the evidence is strong.

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
- Why might this investment FAIL?
- Assume the stock drops 50% next year. What would be the most likely cause?

OUTPUT FORMAT INSTRUCTIONS (JSON ONLY):
1. **Rich Markdown Required:** The strings inside the JSON values must aggressively use Markdown.
2. **Tables:** Use Markdown tables to compare metrics across different years or to list competitors/segments.
3. **Lists & Styling:** Use bolding (`**bold**`), bullet points (`-`), and blockquotes (`>`) to make the analysis highly readable and punchy.
4. **Citations:** Every qualitative claim must end with a page number citation (e.g., `(p. 42)`).

JSON STRUCTURE:
{{
    "recommendation": "Buy / Watch / Avoid",
    "conviction_score": (1-10, be objective, reward strong evidence),
    "is_10_bagger_candidate": true/false,
    "global_thought": "Synthesize the overarching business reality, industry ecosystem, and macroeconomic context. Identify the main structural barrier, but maintain an objective stance based on the evidence.",
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

def get_quarterly_update_prompt(stock: dict, doc_names: list, previous_thesis: str, custom_question: str = None) -> str:
    """Returns the Quarterly Update prompt to verify if the previous thesis still holds."""
    
    current_date = datetime.datetime.now().strftime('%B %d, %Y')
    custom_directive = f"\n\nUSER'S CUSTOM INVESTIGATION DIRECTIVE:\n{custom_question}\nYou MUST explicitly investigate these specific questions. Weave your findings and answers naturally into your analysis.\n" if custom_question else ""
    
    return f"""
Act as a senior forensic equity analyst conducting an interim/quarterly review of a previously analyzed stock.

TARGET: {stock['name']} ({stock.get('ticker', stock['isin'])})
CURRENT DATE: {current_date}
NEW DOCUMENTS TO ANALYZE: {', '.join(doc_names) if doc_names else 'None'}

PREVIOUS INVESTMENT THESIS (The rationale we are checking against):
\"\"\"
{previous_thesis}
\"\"\"

METRICS CONTEXT (Live from Yahoo Finance):
- Trailing P/E: {stock.get('trailing_pe', 'N/A')}
- Forward P/E: {stock.get('forward_pe', 'N/A')}
- EV/EBITDA: {stock.get('ev_to_ebitda', 'N/A')}
- **Raw Enterprise Value (EV):** {stock.get('enterprise_value', 'N/A')}
- **Raw EBITDA:** {stock.get('ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}
- Revenue Growth: {stock.get('revenue_growth', 'N/A')}
- Profit Margins: {stock.get('profit_margins', 'N/A')} 
- Operating Margins: {stock.get('operating_margins', 'N/A')}
- Return on Equity (ROE): {stock.get('return_on_equity', 'N/A')}
- Total Debt: {stock.get('total_debt', 'N/A')}
- Debt to Equity: {stock.get('debt_to_equity', 'N/A')}
- Free Cash Flow: {stock.get('free_cashflow', 'N/A')}{custom_directive}

OBJECTIVE:
Read the new interim/quarterly report. Your sole goal is to determine if the PREVIOUS INVESTMENT THESIS still holds true, or if there are new red flags that act as a SELL SIGNAL.
CRITICAL DIRECTIVE: Before diving into thesis tracking, step back and provide a "Global Thought". What are the broader market realities and macroeconomic shifts impacting the quarter? You must take an objective look, evaluating if the original thesis is deteriorating based on the new data, without being overly pessimistic if the numbers are strong.
You are looking for:
- Margin compression or deteriorating unit economics.
- Slowing growth or loss of market share.
- Management pivoting away from the core strategy (Diworsification).
- The "Gate" (Moat) being breached by competitors.
- Unjustified spikes in capital intensity or debt.

OUTPUT FORMAT INSTRUCTIONS (JSON ONLY):
1. Rich Markdown Required for the string values.
2. Tables: Use Markdown tables where comparing previous vs new numbers if applicable.
3. Citations: Cite the page number from the new report for any claims (e.g., `(p. 14)`).

JSON STRUCTURE:
{{
    "recommendation": "Hold / Sell / Buy More",
    "thesis_holds": true/false,
    "global_thought": "Synthesize the broader market realities impacting this quarter. Document your objective evaluation of whether the ongoing thesis is currently at risk.",
    "analysis": {{
        "thesis_tracking": "Does the new data support the original thesis? What has changed?",
        "financial_update": "Analyze the new revenue, margins, and cash flow. Any deterioration?",
        "red_flags": "List any new red flags discovered in this report.",
        "management_tone": "How is management handling current challenges? Any shifts in strategy?",
        "valuation_check": "Does the current valuation still make sense given the new data?"
    }},
    "verdict_summary": "[QUARTERLY REVIEW] A blunt summary of whether to hold or sell based on the new data."
}}
"""
