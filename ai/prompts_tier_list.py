import json

def get_tier_list_company_analysis_prompt(stock: dict, methodology: str) -> str:
    """Prompt for Stage 1: Deep dive analysis of a single 'Good' company for the tier list."""
    
    return f"""
Act as a world-class quantitative equity researcher and forensic analyst.
Your objective is to execute a relentless, mathematically rigorous analysis of this ONE SPECIFIC candidate for a "Tier List" of hyper-growth micro-cap equities.

TARGET: {stock['name']} ({stock.get('ticker', stock['isin'])})

AVAILABLE METRICS (The Quantitative Launchpad):
- Market Cap: {stock.get('market_cap', 'N/A')}
- Float: {stock.get('float_shares', 'N/A')}
- Gross Margin: {stock.get('gross_margins', 'N/A')}
- Operating Margin: {stock.get('operating_margins', 'N/A')}
- Profit Margin: {stock.get('profit_margins', 'N/A')}
- Operating Cash Flow: {stock.get('operating_cash_flow', 'N/A')}
- Revenue Growth: {stock.get('revenue_growth', 'N/A')}
- Return on Equity (ROE): {stock.get('return_on_equity', 'N/A')}
- Debt to Equity: {stock.get('debt_to_equity', 'N/A')}
- Free Cash Flow: {stock.get('free_cashflow', 'N/A')}

VALUATION CONTEXT (Live from Yahoo Finance):
- Trailing P/E: {stock.get('trailing_pe', 'N/A')}
- Forward P/E: {stock.get('forward_pe', 'N/A')}
- EV/EBITDA: {stock.get('ev_to_ebitda', 'N/A')}
- Enterprise Value (EV): {stock.get('enterprise_value', 'N/A')}
- EBITDA: {stock.get('ebitda', 'N/A')}
- Price/Book: {stock.get('price_to_book', 'N/A')}
- Price/Sales: {stock.get('price_to_sales', 'N/A')}

METHODOLOGY TO APPLY STRICTLY:
\"\"\"
{methodology}
\"\"\"

OBJECTIVE:
Analyze this single company strictly through the lens of the 5 Dimensions provided in the Methodology. 
You are establishing the "Z-Score" logic for this candidate before it is compared against others.
If you have access to an Annual Report document, use it extensively to answer these questions. If not, use the provided metrics and your knowledge of the business model.

OUTPUT FORMAT INSTRUCTIONS:
Ensure to output only raw, beautifully formatted GitHub Flavored Markdown (NO JSON).
Use headers (##), bold text, tables, and bullet points.
CRITICAL: Do not provide a final tier yet, just the raw constituent analysis that will be used later.

Structure the Markdown output EXACTLY like this:

# {stock['name']} ({stock.get('ticker', stock['isin'])}) - Tier List Profile

## Dimension I: Moat Durability and Margin Expansion
*Assess ROIC vs WACC spread, ROIC decay, gross margin stability, and SG&A efficiency.*

## Dimension II: Capital Efficiency (ROIIC)
*Assess Return on Incremental Invested Capital and the 'Right to Grow'. Is this an Ant or a Grasshopper? Evaluate the 3GP score if applicable.*

## Dimension III: Growth-Adjusted Valuation
*Assess EV/GP, PEG, and Growth-Adjusted EV/Sales. Is the price tag justified by the growth velocity?*

## Dimension IV: Market Runway (TAM, SAM, SOM)
*Assess the Serviceable Obtainable Market (SOM) and current market penetration rate. Any saturation risk?*

## Dimension V: Forensic Downside Risk
*Assess Cash Runway, Margin of Safety, Altman Z-Score probability, and Quality of Earnings (Accruals Ratio/Free Cash Flow conversion).*

## Final Analyst Synthesis
*A 2-3 paragraph brutal summary of why this company will or will not achieve exponential returns based on the 5 dimensions.*
"""

def get_tier_list_comparison_prompt(all_analyses: str, methodology: str) -> str:
    """Prompt for Stage 2: Comparing all analyzed companies and ranking them."""
    
    return f"""
Act as the Head of Quantitative Equity Research for a premier micro-cap hedge fund.
You have tasked your analysts to evaluate a curated basket of "Good" companies using your proprietary "Calculus of Outperformance" methodology.

METHODOLOGY REMINDER:
\"\"\"
{methodology}
\"\"\"

Below are the detailed, dimension-by-dimension profiles for every single candidate in the cohort:

\"\"\"
{all_analyses}
\"\"\"

OBJECTIVE:
Synthesize all the individual profiles and produce the definitive Hierarchical Tier List Ranking.
You must objectively rank these companies against each other based strictly on the 5 Dimensions and the associated Non-Linear Allocation weighting from the methodology.
You must penalize "one-trick ponies" (e.g., high growth but terrible unit economics or massive downside risk).

OUTPUT FORMAT INSTRUCTIONS:
Output only raw, highly polished GitHub Flavored Markdown (NO JSON). Do not use a markdown code block identifier.

Structure your final report EXACTLY like this:

# The Calculus of Outperformance: Official Tier List Ranking
*A multi-factor, cross-sectional evaluation of our curated hyper-growth cohort.*

## S-Tier: The Compounders (Unicorns)
*Companies exhibiting elite capital efficiency, impenetrable moats, massive runways, and an acceptable margin of safety. These are the highest probability multi-baggers.*
**(For each company here, provide a bulleted paragraph explaining exactly why it beat the lower tiers, citing specific dimensions like 3GP or Margin Stability).**

## A-Tier: High-Probability Contenders
*Excellent businesses that fall slightly short of S-Tier due to valuation premiums, minor margin decay, or slightly higher penetration rates.*
**(For each company, explain what holds it back from S-Tier).**

## B-Tier: The "Show Me" Story (Hares)
*Companies with high top-line growth but structural flaws in capital efficiency (e.g., burning cash to grow, poor ROIC, low gross margins). They have potential but unacceptable risk-adjusted profiles currently.*
**(For each company, explain the primary mathematical/structural flaw).**

## C-Tier / F-Tier: The Value Traps & Disqualifications
*Companies that failed the forensic downside risk assessment (Altman Z-Score flags, severe accruals) or have completely saturated their TAM.*
**(For each, cite the fatal flaw).**

---

## The Verdict: Portfolio Allocation Strategy
*Provide a 2-paragraph summary on how capital should be allocated across this specific cohort right now.*
"""
