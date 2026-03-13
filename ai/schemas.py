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
    business_description: str = Field(description="A concise summary of what the business actually does, how it makes money, and its primary products/services (The 'Peter Lynch Story').")
    growth_catalysts: Optional[str] = Field(None, description="Mentions of new product launches, major contract wins, regulatory approvals, or capacity expansions that could act as 'Rocket Fuel' for earnings.")
    structural_moat_evidence: Optional[str] = Field(None, description="Evidence of switching costs, network effects, or cost advantages. Cite specific pages/sections.")
    intelligent_fanatic_markers: Optional[str] = Field(None, description="Evidence of extreme frugality, quality obsession, or high insider alignment/integrity. Cite pages.")
    diworsification_red_flags: Optional[str] = Field(None, description="Evidence of unrelated acquisitions subsidized by a profitable core segment.")
    aggressive_accounting_flags: Optional[str] = Field(None, description="Mentions of percentage-of-completion assumption changes, capitalization of routine costs, or segment shuffling.")
    management_tone: str = Field(description="A concise summary of the management's tone (e.g., 'Promotional and defensive', 'Candid and operationally focused').")
    valuation_commentary: Optional[str] = Field(None, description="Mentions of share buyback authorizations, insider buying, or management's view on the company's intrinsic value.")

class FinalAnalysisDetailsSchema(BaseModel):
    """The detailed sections of the final markdown report."""
    forensic_launchpad: str = Field(description="A fluid, highly readable summary of the verified financial data (Revenue, Margins, Debt) highlighting notable trends. Do NOT output raw JSON.")
    the_story: str = Field(description="The 'Peter Lynch Story': a readable summary of what the business does and how it makes money.")
    the_gate: str = Field(description="A fluid discussion of the company's structural moats based on the extracted evidence.")
    rocket_fuel: str = Field(description="A fluid discussion of growth catalysts based on the extracted evidence.")
    intelligent_fanatics: str = Field(description="A fluid discussion of management alignment, frugality, and obsession with quality.")
    valuation: str = Field(description="A fluid discussion of valuation commentary, buybacks, or insider buying.")
    red_flags: str = Field(description="A fluid discussion of any diworsification or aggressive accounting red flags.")
    pre_mortem: str = Field(description="The bear case / what could fundamentally go wrong with this thesis.")

class FinalAnalysisOutputSchema(BaseModel):
    """The root schema for the Synthesis Agent."""
    recommendation: str = Field(description="The final verdict (e.g., 'Strong Buy', 'Watchlist', 'Avoid').")
    conviction_score: int = Field(description="Conviction score from 1 to 10 based on the strength of the moats and financials.")
    is_10_bagger_candidate: bool = Field(description="True if the company has high ROIIC, strong moats, and massive growth potential.")
    global_thought: str = Field(description="A synthesis of the management's tone, the fundamental reality of the business, and its overall quality.")
    verdict_summary: str = Field(description="A crisp, 2-3 sentence executive summary of the entire investment thesis.")
    analysis: FinalAnalysisDetailsSchema = Field(description="The structured markdown content for the report.")
