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
- **M&A Status**: {'⚠️ HEAVY ACQUIRER (Inorganic Growth)' if stock.get('is_acquirer') else 'Organic Growth'}


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
Provide a highly readable, engaging, and jargon-free "Lite" introduction and analysis.
The user's perspective: "I see these crazy good stats on my dashboard. Who are these guys? What do they actually make/sell? Why are the numbers so good right now? And what's the catch?"

CRITICAL RULES:
1. **NO JARGON IN THE INTRO:** Explain the business like you're talking to a smart friend at a dinner party. "They make X for Y." Not "They are a synergistic omnichannel solutions provider."
2. **THE CATALYST:** Since this company appeared on a high-upside dashboard, there is likely a reason. A huge contract? A secular trend? A product launch? A massive price fluctuation? Find it and explain it simply.
3. **GROUND THE NUMBERS:** Connect their abstract financial metrics to their real-world business model. Do not arbitrarily penalize them if they have high margins and low valuations, but be objective.

If the company is flagged as a 'HEAVY ACQUIRER', you MUST address the risk of roll-up strategies, goodwill impairment, and poor organic growth in your reality check.

OUTPUT FORMAT (JSON ONLY):
{{
    "recommendation": "Buy / Watch / Avoid",
    "conviction_score": (1-5 scale. 1: Poor, 3: Average, 5: Exceptional. Use the anchors below),
    "conviction_anchors": {{
        "1": "High risk, poor metrics, or declining business.",
        "3": "Solid business with fair valuation and standard catalysts.",
        "5": "Exceptional compounder with deep moat and massive upside."
    }},
    "is_10_bagger_candidate": true/false,
    "verdict_summary": "A punchy, 2-sentence final takeaway. Are they legitimately a great business or just a speculative flash in the pan?",
    "analysis": {{
        "company_introduction": "What does this company actually do? Explain their core product, their customers, and how they make money in plain English. No corporate buzzwords. Make it extremely clear and accessible.",
        "catalyst_explanation": "Why are the numbers popping? If there is something happening right now that explains a huge price fluctuation, explosive growth, or exceptional margins, explain what that 'big thing' is.",
        "metrics_and_valuation": "The Reality Check. The dashboard shows great stats, but are they sustainable? Look at their debt, cash flow, and valuation (P/E, P/S). Is the market pricing them for perfection?",
        "risks_and_unknowns": "The Catch. Every great story has risks. What are the obvious downsides? Is the industry too capital intensive? What are the biggest unanswered questions we'd need an Annual Report for?"
    }}
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
- **M&A Status**: {'⚠️ HEAVY ACQUIRER (Inorganic Growth)' if stock.get('is_acquirer') else 'Organic Growth'}


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
- Free Cash Flow: {stock.get('free_cashflow', 'N/A')}

ADVANCED 10-BAGGER CALCULUS METRICS:
- Historical ROIC Array: {stock.get('roic_historical', 'DATA NOT FOUND')}
- ROIC Decay Rate: {stock.get('roic_decay_rate', 'DATA NOT FOUND')}
- ROIIC: {stock.get('roiic', 'DATA NOT FOUND')}
- Gross Margin Stability (Std Dev): {stock.get('gross_margin_stability', 'DATA NOT FOUND')}
- SG&A Efficiency Delta: {stock.get('sga_efficiency_delta', 'DATA NOT FOUND')}
- 3GP Score: {stock.get('three_gp_score', 'DATA NOT FOUND')}
- Altman Z-Score: {stock.get('altman_z_score', 'DATA NOT FOUND')}
- Accruals Ratio: {stock.get('accruals_ratio', 'DATA NOT FOUND')}
- Cash Runway Months: {stock.get('cash_runway_months', 'DATA NOT FOUND')}
- **DYNAMIC PROXY WACC (Risk-Adjusted):** {stock.get('proxy_wacc', '0.10')}

**CRITICAL INSTRUCTION ON MISSING DATA:** 
If metrics are marked as 'DATA NOT FOUND', do NOT assume values of zero or penalize the company. This indicates a gap in the external API. You MUST manually hunt for these specific values inside the provided PDF and use the actual document as the definitive override.

**TEMPORAL CONTEXT WARNING:**
The quantitative metrics provided above from 'Yahoo Finance/API' are real-time or TTM (Trailing Twelve Months), representing the stock's current market reality. The PDF documents provided are historical (Annual or Interim reports). You MUST reconcile these two data sources. If the PDF lacks a recent metric found in the API, the API is likely more current. Conversely, if the API has 'DATA NOT FOUND', the PDF is your baseline for structural health, even if it is months older. Always state the date of the document you are citing.
{custom_directive}

OBJECTIVE:
Conduct a brutal, evidence-based deep dive using the provided Annual Report PDF to determine if this stock has the physics to be a 10-Bagger.
CRITICAL DIRECTIVE: First, synthesize a "Global Thought". Understand the absolute reality of this business ecosystem, secular trends, and broader market positioning BEFORE looking for the "Rocket Fuel". You must act as a disciplined, objective analyst. Identify the primary structural barriers or risks, but weigh them fairly against the quantitative metrics and the deep dive evidence. Do not auto-penalize a stock if the evidence is strong.
If the company is flagged as a 'HEAVY ACQUIRER', aggressively search the PDF for signs of 'diworsification', poor acquisition integration, ballooning goodwill, and stagnant organic growth.
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
    "conviction_score": (1-5 scale. 1: High Risk/Value Destructive, 3: Solid/Self-Funding, 5: Elite Compounder. Use the behavioral anchors in the system rubric),
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


def get_tier_list_comparison_prompt(all_analyses: str, methodology: str) -> str:
    """Prompt for Stage 2: Synthesis and Hierarchical Ranking."""
    
    return f"""
Act as the authoritative Lead Quantitative AI of a premier micro-cap hedge fund.
You have directly calculated the mathematics (Z-Scores, Weightings, and Ranking) to generate the exact cohort data provided below.

YOUR OBJECTIVE:
Your task is to review the mathematical cohort data you produced and write a definitive, hierarchical Tier List report explaining the outcome.

**STRICT DIRECTIVE:** Your role is to provide synthesis based ONLY on the numbers provided. Do not guess or hallucinate reasons for a rank—cite the exact sub-dimension scores (e.g., score_moat, score_efficiency, score_risk, score_growth_val) and underlying metrics to mathematically justify every placement. Do NOT override your mathematical order unless you identify a catastrophic qualitative "Red Flag" from your latent knowledge (e.g., known fraud) that the quantitative metrics missed.

**MATHEMATICAL COHORT RANKING:**
{all_analyses}

**METHODOLOGY:**
\"\"\"
{methodology}
\"\"\"

**INSTRUCTIONS:**
1. **Explain the Math**: For each tier and individual company, strictly explain *why* they were categorized there based on their specific dimension scores (e.g., "An outstanding score_efficiency of 2.4 pushed it to S-Tier despite a median score_growth_val").
2. **Missing Data Handling**: If companies have 'DATA NOT FOUND' labels, flag them for manual verification but do not penalize their ranking if they otherwise scored well.

OUTPUT FORMAT INSTRUCTIONS:
Output only raw, highly polished GitHub Flavored Markdown (NO JSON). Do not use a markdown code block identifier.

Structure your final report EXACTLY like this:

# The Calculus of Outperformance: Official Tier List Ranking

## Executive Summary
[Brief overview of the cohort quality]

## 🏆 S-Tier: The Compounders
[Summary of why these companies are the top mathematical candidates]

## 🥇 A-Tier: High-Quality Growth
[Summary...]

## 🥈 B-Tier: Respectable Candidates
[Summary...]

## 🥉 C-Tier: Speculative / High Risk
[Summary...]

## 📉 Red Flag / Avoid
[Companies with catastrophic Z-scores or risks]
"""

def get_calendar_extraction_prompt(current_date: str) -> str:
    """Prompt for extracting corporate events from a calendar PDF."""
    return f"""
Act as a precise data extraction specialist.
I am providing you with a PDF document that is a corporate 'Financial Calendar' or 'Investor Agenda'.
TODAY'S DATE: {current_date}

Your objective is to extract ALL upcoming corporate events from the document that are occurring ON OR AFTER today's date.

OUTPUT FORMAT:
Output ONLY a raw JSON array of objects. Do not include markdown code blocks.
Each object must have exactly these two keys:
1. "date": The date of the event in YYYY-MM-DD format.
2. "event": A concise, professional description of the event (e.g., "Full Year 2025 Earnings").

If no upcoming events are found, return an empty array [].
"""


