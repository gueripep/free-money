from pydantic import BaseModel, Field
from typing import Optional, List

class FinancialYearData(BaseModel):
    """Represents core financial data for a specific year to enable ROIIC and Z-Score math."""
    year: int = Field(description="The fiscal year (e.g., 2023)")
    
    # Income/Operations
    total_revenue: Optional[float] = Field(None, description="Reported Total Net Revenue / Sales / Turnover.")
    cogs: Optional[float] = Field(None, description="Cost of Goods Sold / Cost of Revenue.")
    gross_profit: Optional[float] = Field(None, description="Total Revenue minus COGS.")
    sga: Optional[float] = Field(None, description="Selling, General and Administrative expenses. MUST exclude R&D if listed separately.")
    rnd: Optional[float] = Field(None, description="Research & Development expenses.")
    ebit: Optional[float] = Field(None, description="Earnings Before Interest and Taxes (Operating Income). Exclude interest and taxes.")
    net_income: Optional[float] = Field(None, description="Net Income applicable to common shareholders.")
    effective_tax_rate: Optional[float] = Field(None, description="Effective tax rate percentage (e.g., 0.21 for 21%).")
    
    # Balance Sheet (Assets)
    total_assets: Optional[float] = Field(None, description="Total Assets.")
    current_assets: Optional[float] = Field(None, description="Total Current Assets.")
    cash_and_equivalents: Optional[float] = Field(None, description="Cash, cash equivalents, and short-term highly liquid investments.")
    accounts_receivable: Optional[float] = Field(None, description="Net Accounts Receivable.")
    inventory: Optional[float] = Field(None, description="Net Inventory.")
    net_ppe: Optional[float] = Field(None, description="Net Property, Plant, and Equipment.")
    
    # Balance Sheet (Liabilities & Equity)
    total_liabilities: Optional[float] = Field(None, description="Total Liabilities.")
    current_liabilities: Optional[float] = Field(None, description="Total Current Liabilities.")
    financing_liabilities: Optional[float] = Field(None, description="Short-term interest-bearing debt nested in current liabilities (e.g., current portion of long term debt, notes payable).")
    retained_earnings: Optional[float] = Field(None, description="Retained Earnings or Accumulated Deficit.")
    total_equity: Optional[float] = Field(None, description="Total Stockholders' Equity.")

class TableExtractionSchema(BaseModel):
    """The root schema for the Table Extraction Agent."""
    company_name: str = Field(description="The name of the company.")
    fiscal_years_extracted: List[FinancialYearData] = Field(description="A list of objects, one for each fiscal year found in the tables (typically 2 to 3 years covering the presented periods).")
    
class QualitativeForensicsSchema(BaseModel):
    """The root schema for the Narrative Forensic Agent."""
    # --- Mandatory opener ---
    company_introduction: str = Field(description="A plain-language paragraph explaining what this company does, who its customers are, and where it sits in its market. No jargon, no hype, no superlatives. Written as if the reader has never heard of the company. One paragraph maximum.")
    business_description: str = Field(description="A concise summary of what the business actually does, how it makes money, and its primary products/services.")

    # --- Bullish lenses (each paired with a skeptical mirror) ---
    growth_catalysts: Optional[str] = Field(None, description="Mentions of new product launches, major contract wins, regulatory approvals, or capacity expansions that could sustainably accelerate earnings.")
    growth_quality_concerns: Optional[str] = Field(None, description="Skeptical mirror: Is this growth durable or pulled forward? Evidence of one-time windfalls, channel stuffing, unsustainable discounting, or customer concentration that inflates the growth narrative.")

    structural_moat_evidence: Optional[str] = Field(None, description="Evidence of switching costs, network effects, or cost advantages. Cite specific pages/sections.")
    moat_fragility_evidence: Optional[str] = Field(None, description="Skeptical mirror: Evidence that the moat is eroding — rising competitive pressure, low barriers to entry, commoditization, or technology disruption. Cite pages.")

    intelligent_fanatic_markers: Optional[str] = Field(None, description="Evidence of extreme frugality, quality obsession, or high insider alignment/integrity. Cite pages.")
    management_risk_flags: Optional[str] = Field(None, description="Skeptical mirror: Evidence of empire-building, promotional tone in filings, key-person dependency, excessive executive compensation, or insider selling. Cite pages.")

    # --- Standalone Red Flags (equally weighted, not a footnote) ---
    red_flags_diworsification: Optional[str] = Field(None, description="Evidence of unrelated acquisitions subsidized by a profitable core segment.")
    red_flags_accounting: Optional[str] = Field(None, description="Mentions of percentage-of-completion assumption changes, capitalization of routine costs, segment shuffling, or any other aggressive accounting practices.")
    red_flags_other: Optional[str] = Field(None, description="Any other material red flags not covered above (e.g., regulatory risk, litigation, related-party transactions).")

    management_tone: str = Field(description="A concise summary of the management's tone (e.g., 'Promotional and defensive', 'Candid and operationally focused').")
    valuation_commentary: Optional[str] = Field(None, description="Mentions of share buyback authorizations, insider buying, or management's view on the company's intrinsic value.")

class BlindQualitativeExtractionSchema(BaseModel):
    """The root schema for Phase 1: Blind Extraction."""
    value_proposition: str = Field(description="Purely qualitative description of the core product/service and the problem it solves. NO NAMES.")
    revenue_engine: str = Field(description="Mechanism of value capture (subscription, transactional, etc.). NO NUMBERS.")
    cost_structure: str = Field(description="Fixed vs. variable cost dynamics and capital intensity. NO MARGINS.")
    customer_dynamics: str = Field(description="Client concentration and behavior. NO EXACT COUNTS.")
    primary_target_customers: str = Field(description="Detailed profile of the ideal customer (e.g., 'Medium-sized regional banks'). NO NAMES.")
    industry_context: str = Field(description="The specific industry and market niche (e.g., 'Video Game Developer specializing in RPGs'). DO NOT use the company name.")
    strategic_maneuvers: str = Field(description="Tactical changes management is making (e.g., 'Increasing salaries to prevent talent drain').")
    future_catalysts_detailed: str = Field(description="Long-form description of upcoming product launches, market expansions, etc.")
    distribution_supply: str = Field(description="Supply chain complexity. NO LOCATIONS.")
    competitive_positioning: str = Field(description="Competitive landscape and perceived differentiation. NO MARKET SHARE %.")
    management_outlook: str = Field(description="Forward-looking strategic initiatives. NO DATES OR TARGETS.")

class PorterFiveForces(BaseModel):
    new_entrants: str
    supplier_power: str
    buyer_power: str
    substitutes: str
    rivalry: str

class SevenPowers(BaseModel):
    scale_economies: Optional[str]
    network_economies: Optional[str]
    switching_costs: Optional[str]
    counter_positioning: Optional[str]
    cornered_resource: Optional[str]
    branding: Optional[str]
    process_power: Optional[str]

class BlindQualitativeEvaluationSchema(BaseModel):
    """The root schema for Phase 2: Blind Evaluation."""
    mechanistic_summary: str = Field(description="How the business creates and captures value.")
    primary_target_customers: str = Field(description="Detailed profile of the ideal customer (e.g., 'Medium-sized regional banks', 'High-net-worth retail investors').")
    industry_context: str = Field(description="The specific industry and market niche.")
    strategic_maneuvers: str = Field(description="Tactical changes management is making.")
    future_catalysts_detailed: str = Field(description="Long-form description of upcoming catalysts.")
    porter_analysis: PorterFiveForces
    seven_powers: SevenPowers
    moat_rating: str = Field(description="Wide, Narrow, or None.")
    capital_efficiency: str = Field(description="Assessment of marginal cost for growth.")
    primary_structural_risks: str = Field(description="The top 3 structural risks that could break the business model.")
    tactical_conflicts: str = Field(description="Internal contradictions or tensions in the model.")
    competitive_moat_sustainability: str = Field(description="Detailed analysis of why the moat will or will not last 10 years.")
    talent_and_culture_risk: str = Field(description="Analysis of 'Brain Drain' or human capital dependency.")
    structural_tier: int = Field(description="1 (Exceptional), 2 (Defensible but Capital Intensive), 3 (Commoditized/Fragile).")
    final_verdict: str = Field(description="Crisp final decision on structural quality.")

class FinalAnalysisDetailsSchema(BaseModel):
    """The detailed sections of the final markdown report. No investor framework labels (Lynch, O'Neil, etc.) — neutral headings only."""
    company_introduction: str = Field(description="The plain-language company introduction. No superlatives, no verdict, no framing. Just what the company does and where it sits in its market.")
    forensic_launchpad: str = Field(description="A fluid, highly readable summary of the verified financial data (Revenue, Margins, Debt) highlighting notable trends. Do NOT output raw JSON.")
    competitive_moat: str = Field(description="A balanced discussion of the company's structural moats AND their fragilities, based on the extracted evidence.")
    growth_catalysts_and_risks: str = Field(description="A balanced discussion of growth catalysts alongside growth quality concerns — is this growth durable or pulled forward?")
    management_quality: str = Field(description="A balanced discussion of management alignment and quality alongside management risk flags (empire-building, key-person risk, compensation).")
    valuation: str = Field(description="A fluid discussion of valuation relative to the business quality, including buybacks or insider buying signals.")
    red_flags: str = Field(description="A standalone, equally-weighted discussion of ALL red flags: diworsification, aggressive accounting, and any other material concerns. This is NOT a footnote.")
    conviction_scorecard: str = Field(description="A Markdown table showing 5 dimensions scored 1-10: Revenue Growth Quality, Moat Durability, Capital Efficiency, Management Quality, Risk Profile. Include weights (25/25/20/15/15) and the computed weighted average.")
    bull_bear_disagreements: str = Field(description="Explicit reconciliation of contradictions between the bull case and the skeptical case. Do not reference agents or evaluations by name. MANDATORY if the evaluation rated Moat Durability as Narrow or below. Must appear before any investment conclusion.")
    pre_mortem: str = Field(description="The bear case / what could fundamentally go wrong with this thesis.")

class FinalAnalysisOutputSchema(BaseModel):
    """The root schema for the Synthesis Agent."""
    recommendation: str = Field(description="The final verdict (e.g., 'Strong Buy', 'Watchlist', 'Avoid'). Must follow FROM the scorecard, not precede it.")
    
    scoring_rationale: str = Field(
        description=(
            "MANDATORY: Provide a balanced synthesis of the evidence-based strengths and material risks. "
            "Evaluate the company's prospects objectively, weighing the 'Rocket Fuel' against the 'Structural Barriers'."
            "This reasoning MUST be written BEFORE the scores are determined."
        )
    )

    # --- Five independently scored dimensions (1-5) ---
    score_revenue_growth_quality: int = Field(
        description=(
            "Revenue Growth Quality (1-5). "
            "1: Revenue declining or flat with no credible growth catalyst. "
            "2: Low single-digit growth, heavily dependent on one-time or inorganic drivers. "
            "3: Moderate organic growth (5-10%) but limited evidence of durability or TAM expansion. "
            "4: Strong, durable organic growth (10-20%) with clear catalysts and reasonable visibility. "
            "5: Exceptional, multi-year organic growth (20%+) with widening TAM and structural tailwinds."
        )
    )
    score_moat_durability: int = Field(
        description=(
            "Moat Durability (1-5). "
            "1: No discernible moat; highly commoditized business with low switching costs. "
            "2: Weak/Narrow moat; some branding or niche focus but easily disrupted. "
            "3: Respectable moat; clear differentiation or cost advantage but facing active competition. "
            "4: Strong moat; high switching costs, network effects, or unique scale efficiencies. "
            "5: Fortress moat; dominant market position with multi-decade structural protection (Helmer's 7 Powers)."
        )
    )
    score_capital_efficiency: int = Field(
        description=(
            "Capital Efficiency (1-5). "
            "1: Value destructive; ROIC < WACC and consistently burning cash. "
            "2: Marginal; ROIC roughly equals WACC, requires heavy CapEx to sustain growth. "
            "3: Solid; Self-funding operations with ROIC > 10%. "
            "4: High; Asset-light scalability with ROIC > 20% and strong FCF generation. "
            "5: Elite; Infinite-buffer scalability with ROIC > 30% and exceptional unit economics."
        )
    )
    score_management_quality: int = Field(
        description=(
            "Management Quality (1-5). "
            "1: Misaligned/Promotional; aggressive compensation, low insider ownership, vague strategy. "
            "2: Average; capable but unremarkable; standard compensation and conventional strategy. "
            "3: Competent; clear track record, honest communication, and decent alignment. "
            "4: High; Intelligent Fanatic markers; owner-operator mindset and extreme operational focus. "
            "5: Visionary/Steward; Exceptional capital allocation history, high insider ownership (>10%), and radical candor."
        )
    )
    score_risk_profile: int = Field(
        description=(
            "Risk Profile (1-5, where 5 = lowest risk). "
            "1: Catastrophic Risk; terminal debt, regulatory investigation, or failing business model. "
            "2: High Risk; high leverage, intense competition, or aggressive accounting markers. "
            "3: Moderate Risk; standard cyclical or operational risks, manageable debt levels. "
            "4: Low Risk; clean balance sheet (or net cash), diverse customer base, and clear regulatory path. "
            "5: Antifragile; significant net cash position, essential service status, and robust margins."
        )
    )
    conviction_score: float = Field(description="Weighted average of the five dimension scores (1-5). Weights: Revenue Growth Quality 25%, Moat Durability 25%, Capital Efficiency 20%, Management Quality 15%, Risk Profile 15%. MUST be computed, not intuited.")
    is_10_bagger_candidate: bool = Field(description="True if the company has high ROIIC, strong moats, and massive growth potential.")
    global_thought: str = Field(description="A synthesis of the fundamental reality of the business, its competitive position, and overall quality.")
    verdict_summary: str = Field(description="A crisp, 2-3 sentence executive summary of the entire investment thesis. Must follow from the scorecard.")
    analysis: FinalAnalysisDetailsSchema = Field(description="The structured markdown content for the report.")
    structural_quality_blind: Optional[BlindQualitativeEvaluationSchema] = Field(None, description="The results of the blind qualitative evaluation.")
