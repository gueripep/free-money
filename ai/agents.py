from ai.schemas import TableExtractionSchema, QualitativeForensicsSchema, BlindQualitativeEvaluationSchema, FinalAnalysisOutputSchema
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
        """Extracts qualitative markers from the MD&A and Risk Factors with balanced bull/bear lenses."""
        
        prompt_text = f"""
        You are a senior qualitative forensic analyst performing a balanced extraction.
        Your objective is to read the Management Discussion & Analysis (Item 7) and Risk Factors (Item 1A) of the provided Annual Report.
        
        COMPANY: {company_name}
        
        CRITICAL INSTRUCTIONS:
        For each extraction category, cite your findings (e.g., "(Item 7, pg. 42)").
        Every bullish finding MUST be paired with its skeptical mirror. Do NOT treat skeptical findings as an afterthought.
        
        EXTRACTION CATEGORIES (populate every field in the schema):
        
        **SECTION 0 — COMPANY INTRODUCTION (MANDATORY)**
        Write a single plain-language paragraph explaining what this company does, who its customers are, and where it sits in its market.
        Rules: No jargon. No hype. No superlatives. No investor-speak. Write as if explaining to someone who has never heard of this company. One paragraph maximum.
        
        **SECTION 1 — BUSINESS DESCRIPTION**
        A concise 2-3 sentence summary of what the business sells, how it generates revenue, and to whom.
        
        **SECTION 2 — GROWTH (Bull + Bear)**
        - Growth Catalysts: New product launches, major contract wins, regulatory approvals, or capacity expansions that could sustainably accelerate earnings.
        - Growth Quality Concerns (SKEPTICAL MIRROR): Is this growth durable or pulled forward? Look for one-time windfalls, channel stuffing, unsustainable discounting, heavy customer concentration, or cyclical tailwinds masquerading as structural growth.
        
        **SECTION 3 — MOAT (Bull + Bear)**
        - Structural Moat Evidence: High switching costs, network effects, unique cost advantages, or regulatory barriers.
        - Moat Fragility Evidence (SKEPTICAL MIRROR): Signs the moat is eroding — rising competitive pressure, low barriers to entry, commoditization, technology disruption, or customer alternatives emerging.
        
        **SECTION 4 — MANAGEMENT (Bull + Bear)**
        - Intelligent Fanatic Markers: Extreme frugality, quality obsession, high insider ownership, continuous improvement culture.
        - Management Risk Flags (SKEPTICAL MIRROR): Empire-building, promotional tone in filings, key-person dependency, excessive executive compensation, insider selling.
        
        **SECTION 5 — RED FLAGS (Standalone, Equally Weighted)**
        These are NOT footnotes. Each is a standalone field that must receive equal analytical weight:
        - Diworsification: Unrelated acquisitions subsidized by a profitable core segment.
        - Aggressive Accounting: Changes in revenue recognition, capitalization of routine costs, segment shuffling.
        - Other Red Flags: Regulatory risk, litigation, related-party transactions, or any other material concerns.
        
        **SECTION 6 — MANAGEMENT TONE**
        A 1-sentence summary of how management sounds (e.g., promotional, defensive, pragmatic, candid).
        
        **SECTION 7 — VALUATION COMMENTARY**
        Mentions of share buyback authorizations, insider buying, or management explicitly discussing the company's intrinsic value.
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
        
    def synthesize(self, company_name: str, table_data: TableExtractionSchema, narrative_data: QualitativeForensicsSchema, blind_evaluation_data: BlindQualitativeEvaluationSchema, stock_metrics: dict) -> FinalAnalysisOutputSchema:
        """Synthesizes raw data into a readable, human-friendly markdown report with computed conviction score."""
        from ai.schemas import FinalAnalysisOutputSchema # imported locally to avoid circular dependencies if any
        
        # Detect if we need hard reconciliation (Blind Evaluation rated moat as Narrow or below)
        blind_moat_rating = "N/A"
        if blind_evaluation_data:
            blind_moat_rating = blind_evaluation_data.moat_rating or "N/A"
        moat_is_weak = blind_moat_rating.lower() in ["narrow", "none", "n/a"]
        
        reconciliation_directive = ""
        if moat_is_weak and blind_evaluation_data:
            reconciliation_directive = f"""
        **HARD RECONCILIATION RULE (MANDATORY):**
        The qualitative evaluation rated Moat Durability as '{blind_moat_rating}'.
        You MUST explicitly address this contradiction in the 'bull_bear_disagreements' section BEFORE issuing any verdict.
        This section cannot be empty or dismissive. Explain concretely why you agree or disagree with this assessment,
        citing specific evidence from both the bullish and bearish perspectives.
        The 'bull_bear_disagreements' section MUST appear before the pre-mortem and before any investment conclusion.
        """
        
        prompt_text = f"""
        You are a disciplined, evidence-based Chief Investment Officer synthesizing a deep-dive thesis.
        
        Your job is to translate raw agent data into a fluid, highly-readable markdown report.
        DO NOT output raw JSON arrays in your text. Translate the numbers into readable financial commentary.
        
        **CRITICAL RULES:**
        - NO INVESTOR FRAMEWORK LABELS: Do NOT mention Lynch, O'Neil, Phelps, Cassel, or any named investor framework in the output. These are internal analysis tools only. Use neutral, descriptive section headings.
        - INTEGRATE BLIND EVALUATION: The Blind Evaluation output is source material only. Its findings must be integrated into the relevant sections of the report. It must never appear as a standalone section or be referenced by name. The reader should have no awareness that a separate evaluation pass occurred.
        - NO SUPERLATIVES IN THE OPENING: The document opens with the Company Introduction — a factual description of what the company does, who it serves, and where it sits in its market. No verdict, no framing, no opinion.
        - THE VERDICT FOLLOWS THE SCORECARD: You must score the five dimensions FIRST. The conviction score and recommendation are DERIVED from those scores, not intuited. Do not form an opinion and then reverse-engineer justifications.
        
        **ANTI-INFLATION DIRECTIVE:**
        You are known to systematically inflate scores toward 4/5. This is a documented psychometric bias in AI evaluators. You MUST actively resist this tendency.
        - A score of 5 should be RARE — reserved for truly exceptional, best-in-class evidence.
        - A score of 3 is the TRUE CENTER — it represents a 'decent but unremarkable' company.
        - Scores of 1 and 2 MUST be used when evidence warrants it. Do NOT soften bad findings.
        - If your initial scores average above 3.5, re-examine your rationale for inflation.

        **SCORING EXAMPLES (Calibration):**
        1. Low-Score (1-2): A company with declining revenue, no moat, and heavy debt → Score 1 for Growth and Risk.
        2. Mid-Score (3): Moderate growth but customer concentration risk or high capital intensity → Score 3.
        3. High-Score (5): Exceptional, durable organic growth, widening moat, and net cash position → Score 5.
        
        COMPANY: {company_name}
        
        LIVE MARKET METRICS (From Yahoo Finance):
        {stock_metrics}
        
        VERIFIED FINANCIAL TABLES (From Table Agent):
        {table_data.model_dump_json(indent=2)}
        
        FORENSIC NARRATIVE (From Narrative Agent):
        {narrative_data.model_dump_json(indent=2)}
        
        STRUCTURAL QUALITY EVALUATION (BLIND — performed by an AI with no access to the company name or financials):
        {blind_evaluation_data.model_dump_json(indent=2) if blind_evaluation_data else "N/A"}
        BLIND MOAT RATING: {blind_moat_rating}
        {reconciliation_directive}
        
        INSTRUCTIONS:
        
        1. **Company Introduction** ('company_introduction'): Copy the plain-language Company Introduction from the Narrative Agent verbatim. No superlatives, no verdict, no framing.
        
        2. **Forensic Launchpad** ('forensic_launchpad'): Summarize the revenue and margin trends from the Table Agent data. Use prose, not raw JSON. Highlight inflection points and red-flag trends.
        
        3. **Competitive Moat** ('competitive_moat'): Write a BALANCED discussion. Present the moat evidence from the Narrative Agent AND the moat fragility evidence side by side. Integrate the AI's moat assessment without referencing the agent or evaluation by name.
        
        4. **Growth Catalysts & Risks** ('growth_catalysts_and_risks'): Present the growth catalysts AND the growth quality concerns from the Narrative Agent. Is the growth durable or artificially inflated?
        
        5. **Management Quality** ('management_quality'): Present the intelligent fanatic markers AND the management risk flags. Include compensation, insider ownership, and tone analysis.
        
        6. **Valuation** ('valuation'): Discuss the current valuation (from Yahoo Finance metrics) relative to the quality of the business. Include insider buying/buyback signals.
        
        7. **Red Flags** ('red_flags'): This is a STANDALONE, EQUALLY-WEIGHTED section. Combine all red flags (diworsification, accounting, other) from the Narrative Agent into a comprehensive discussion. Do NOT minimize or footnote these.
        
        8. **Conviction Scorecard** ('conviction_scorecard'): 
           You MUST populate `scoring_rationale` FIRST — listing all weaknesses, then all strengths — BEFORE setting any score fields.
           Score each dimension independently on a 1-5 scale based ONLY on the evidence and the behavioral anchors defined in the schema:
           - Revenue Growth Quality (weight: 25%)
           - Moat Durability (weight: 25%)
           - Capital Efficiency (weight: 20%)
           - Management Quality (weight: 15%)
           - Risk Profile (weight: 15%, where 5 = lowest risk)
           Present as a Markdown table with columns: Dimension | Score | Weight | Weighted Score.
           Include the final weighted average at the bottom.
           **These five scores must also be output in the schema fields**: score_revenue_growth_quality, score_moat_durability, score_capital_efficiency, score_management_quality, score_risk_profile.
           **The conviction_score field must equal the weighted average** (= 0.25*Growth + 0.25*Moat + 0.20*Efficiency + 0.15*Management + 0.15*Risk).
        
        9. **Where the Bull and Bear Cases Disagree** ('bull_bear_disagreements'): Just state "the bull and bear cases disagree on X" without explaining why there are two cases in the first place or referencing the evaluation. If the skeptical moat rating was Narrow or None, this section is MANDATORY and must be substantive but fully integrated as natural analysis.
        
        10. **Pre-Mortem** ('pre_mortem'): The bear case — what could fundamentally break this thesis.
        
        11. **Recommendation and Verdict**: The 'recommendation' and 'verdict_summary' MUST follow FROM the scorecard. They cannot be determined before the scoring is complete.
        
        12. **Blind Evaluation Passthrough**: The 'structural_quality_blind' field in the output schema MUST be populated with the provided Blind Evaluation data.
        
        13. **10-Bagger Flag**: 'is_10_bagger_candidate' should only be true if there is strong moat evidence AND excellent financial trends AND the conviction score is >= 7.
        """
        
        logger.info(f"SynthesisAgent: Generating final readable markdown report for {company_name}...")
        
        result = self.client.generate_structured_content([prompt_text], FinalAnalysisOutputSchema)
        if not result:
            logger.error("SynthesisAgent failed to return a valid schema.")
        return result
