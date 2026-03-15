from typing import List, Optional
from pydantic import BaseModel, Field
from ai.schemas import FinalAnalysisOutputSchema
from ai.gemini_client import GeminiClient
from core.config import setup_logging

logger = setup_logging("score_auditor")

class AuditedScoresSchema(BaseModel):
    """Schema for the ScoreAuditor's output."""
    score_revenue_growth_quality: int
    score_moat_durability: int
    score_capital_efficiency: int
    score_management_quality: int
    score_risk_profile: int
    any_overrides: bool = Field(description="True if any scores were adjusted from the original.")
    adjustments_made: List[str] = Field(description="List of justifications for any score adjustments.")

class ScoreAuditor:
    """
    A Devil's Advocate agent that critiques and calibrates scores from the Synthesis Agent.
    It specifically looks for score inflation and ensures the rationale supports the final integer.
    """
    
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def audit(self, company_name: str, original_analysis: FinalAnalysisOutputSchema) -> AuditedScoresSchema:
        """Audits the scores and returns potentially adjusted values."""
        
        prompt_text = f"""
        Act as a brutal Devil's Advocate and Chief Compliance Officer for a hedge fund.
        Your job is to audit the investment analysis and scores produced by another agent.
        
        COMPANY: {company_name}
        
        ORIGINAL RATIONALE:
        \"\"\"
        {original_analysis.scoring_rationale}
        \"\"\"
        
        ORIGINAL SCORES (1-5 scale):
        - Growth: {original_analysis.score_revenue_growth_quality}
        - Moat: {original_analysis.score_moat_durability}
        - Efficiency: {original_analysis.score_capital_efficiency}
        - Management: {original_analysis.score_management_quality}
        - Risk: {original_analysis.score_risk_profile}
        
        CRITICAL AUDIT DIRECTIVE:
        Look for "generative politeness" and score inflation. If the rationale mentions ANY significant weakness (e.g., customer concentration, high debt, low margins), the score CANNOT be a 5. A 5 is for perfection. A 4 is for excellence. A 3 is average.
        
        For each score, you must either:
        1. **Confirm**: The score is perfectly supported by the evidence.
        2. **Adjust Down**: The rationale shows flaws that the integer score ignored. (Most common)
        3. **Adjust Up**: The rationale shows exceptional strength that was undervalued.
        
        OUTPUT FORMAT:
        You must return the final (potentially adjusted) integer scores and a list of justifications for any changes.
        """
        
        logger.info(f"ScoreAuditor: Auditing scores for {company_name}...")
        
        # We use a standard generate_structured_content call without the Auditor itself being audited (to avoid recursion)
        result = self.client.generate_structured_content([prompt_text], AuditedScoresSchema)
        
        if not result:
            logger.error("ScoreAuditor failed to return a valid schema.")
            # Fallback to original scores if audit fails
            return AuditedScoresSchema(
                score_revenue_growth_quality=original_analysis.score_revenue_growth_quality,
                score_moat_durability=original_analysis.score_moat_durability,
                score_capital_efficiency=original_analysis.score_capital_efficiency,
                score_management_quality=original_analysis.score_management_quality,
                score_risk_profile=original_analysis.score_risk_profile,
                any_overrides=False,
                adjustments_made=["Audit failed - falling back to original scores."]
            )
            
        return result
