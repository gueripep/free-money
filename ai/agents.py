from ai.schemas import TableExtractionSchema, QualitativeForensicsSchema
from ai.gemini_client import GeminiClient
from core.config import setup_logging
import datetime

logger = setup_logging("agents")

class TableExtractionAgent:
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def extract(self, company_name: str, gemini_file=None, cached_content=None) -> TableExtractionSchema:
        """Extracts highly structured quantitative data from the financial tables."""
        
        prompt_text = f"""
        You are a highly precise forensic accounting extraction agent.
        Your sole objective is to populate the provided JSON schema with exact numerical values extracted from the financial statements (Item 8) of the provided Annual Report.
        
        COMPANY: {company_name}
        
        CRITICAL RULES:
        1.  **NO MATH**: Do not calculate ratios (like Z-Score or ROIC) yourself. Only extract the raw historical integers as printed in the tables.
        2.  **MAPPING**: 
            - 'total_revenue' may be labeled as Net Sales, Sales, or Turnover.
            - 'ebit' should be Operating Income (exclude interest and taxes).
            - 'retained_earnings' may be Accumulated Deficit.
            - 'financing_liabilities' means short-term debt, current portion of long-term debt, or notes payable. Do NOT include accounts payable here.
        3.  **SG&A vs R&D**: If Research and Development is listed as a separate line item from SG&A, put it in the 'rnd' field. ONLY put the pure SG&A number in the 'sga' field.
        4.  **MISSING DATA**: If a value genuinely does not exist for a given year, leave it null (None).
        
        Extract data for the primary years presented in the Income Statement, Balance Sheet, and Cash Flow statements.
        """
        
        logger.info(f"TableExtractionAgent: Generating structured data for {company_name}...")
        
        if cached_content:
            result = self.client.generate_structured_content([prompt_text], TableExtractionSchema, cached_content=cached_content)
        else:
            result = self.client.generate_structured_content([prompt_text, gemini_file], TableExtractionSchema)
            
        if not result:
            logger.error("TableExtractionAgent failed to return a valid schema.")
        return result


class NarrativeForensicAgent:
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def extract(self, company_name: str, gemini_file=None, cached_content=None) -> QualitativeForensicsSchema:
        """Extracts qualitative markers from the MD&A and Risk Factors."""
        
        prompt_text = f"""
        You are a senior qualitative forensic analyst.
        Your objective is to read the Management Discussion & Analysis (Item 7) and Risk Factors (Item 1A) of the provided Annual Report and extract specific qualitative markers.
        
        COMPANY: {company_name}
        
        CRITICAL INSTRUCTIONS:
        You must look for the following specific markers and populate the schema. Be concise but cite your findings (e.g., "(Item 7, pg. 42)").
        
        1.  **Business Description**: A very concise, 2-3 sentence summary of what the business actually sells, how it generates revenue, and to whom.
        2.  **Growth Catalysts ("Rocket Fuel")**: Look for mentions of new product launches, major contract wins, regulatory approvals, or capacity expansions that could sustainably accelerate earnings.
        3.  **Structural Moat Evidence**: Look for evidence of high switching costs, network effects, or unique cost advantages.
        4.  **Intelligent Fanatic Markers**: Look for an obsession with quality, extreme cost-consciousness/frugality, high insider ownership mentioned, or a culture of continuous improvement without executive bloat.
        5.  **Diworsification Red Flags**: Mentions of integrating unrelated acquisitions that are dragging down core segment margins.
        6.  **Aggressive Accounting Flags**: Look for changes in revenue recognition ("percentage of completion"), capitalized software costs, or shifting segment definitions.
        7.  **Management Tone**: Provide a 1-sentence summary of how management sounds (e.g., promotional, defensive, pragmatic).
        8.  **Valuation Commentary**: Look for mentions of share buyback authorizations, insider buying, or management explicitly discussing the company's intrinsic value being disconnected from the market price.
        """
        
        logger.info(f"NarrativeForensicAgent: Mining qualitative data for {company_name}...")
        
        if cached_content:
             result = self.client.generate_structured_content([prompt_text], QualitativeForensicsSchema, cached_content=cached_content)
        else:
             result = self.client.generate_structured_content([prompt_text, gemini_file], QualitativeForensicsSchema)
             
        if not result:
            logger.error("NarrativeForensicAgent failed to return a valid schema.")
        return result

class SynthesisAgent:
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def synthesize(self, company_name: str, table_data: TableExtractionSchema, narrative_data: QualitativeForensicsSchema, stock_metrics: dict) -> FinalAnalysisOutputSchema:
        """Synthesizes raw data into a readable, human-friendly markdown report."""
        from ai.schemas import FinalAnalysisOutputSchema # imported locally to avoid circular dependencies if any
        
        prompt_text = f"""
        You are a seasoned Chief Investment Officer (CIO) presenting a deep-dive "10-Bagger" thesis to your portfolio managers.
        
        You have just received the mathematically verified quantitative data and the raw qualitative notes from your forensic accounting team.
        Your job is to translate this raw json data into a fluid, highly-readable, and compelling markdown report. 
        DO NOT output raw JSON arrays in your text. Translate the numbers into readable financial commentary.
        
        COMPANY: {company_name}
        
        LIVE MARKET METRICS (From Yahoo Finance):
        {stock_metrics}
        
        VERIFIED FINANCIAL TABLES (From Table Agent):
        {table_data.model_dump_json(indent=2)}
        
        FORENSIC NARRATIVE (From Narrative Agent):
        {narrative_data.model_dump_json(indent=2)}
        
        INSTRUCTIONS:
        1. Fill out the final schema using fluid, professional language.
        2. In 'forensic_launchpad', summarize the revenue and margin trends based on the raw table data provided. Do NOT paste the json table. 
        3. Determine the 'is_10_bagger_candidate' flag. It should only be true if there is strong moat evidence AND excellent financial trends.
        4. Provide an overall conviction score out of 10.
        """
        
        logger.info(f"SynthesisAgent: Generating final readable markdown report for {company_name}...")
        
        # We don't necessarily need the PDF context here since this agent just reads the outputs of the previous agents!
        # But we pass the prompt to the structured generator.
        result = self.client.generate_structured_content([prompt_text], FinalAnalysisOutputSchema)
        if not result:
            logger.error("SynthesisAgent failed to return a valid schema.")
        return result
