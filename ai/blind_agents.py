from ai.schemas import BlindQualitativeExtractionSchema, BlindQualitativeEvaluationSchema
from ai.gemini_client import GeminiClient
from core.config import setup_logging

logger = setup_logging("blind_agents")

class BlindExtractionAgent:
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def extract(self, company_name: str, gemini_file=None, cached_content=None) -> BlindQualitativeExtractionSchema:
        """Pass One: Performs a high-insight qualitative extraction with industry context."""
        
        prompt_text = f"""
        You are an elite Buy-Side Equity Research Analyst specializing in structural forensics.
        Your task is to perform an 'Investor-Grade' qualitative extraction of the operational mechanics of the business described in the provided report.
        
        COMPANY: {company_name}
        
        RULES OF ENGAGEMENT:
        1. **NO IDENTIFYING NAMES**: Do not use the company name, product names, or executive names. 
        2. **ALLOW INDUSTRY CONTEXT**: You SHOULD identify the specific industry and market niche (e.g., 'Video Game Developer', 'Insurance Brokerage', 'Vertical SaaS for Banks'). This is critical for strategic context.
        3. **STRICTLY NO NUMBERS**: Remove all absolute financial figures. Abstract them into qualitative descriptions.
        4. **STORY-FIRST EXTRACTION**: Don't just list facts. Explain the *logic* of the business. 
        
        EXTRACTIVE GOALS:
        - **Industry Context**: Define the niche and the laws of physics governing that industry.
        - **Strategic Maneuvers**: Identify the single biggest tactical shift management is making (e.g., salary hikes, pivoting to a new platform, vertical integration).
        - **Future Catalysts**: Detail upcoming launches or expansions that would act as 'Rocket Fuel'.
        - **Value Proposition**: What is the 'Secret Sauce' or the fundamental problem being solved?
        - **Revenue Engine**: Exactly how does a dollar move from a customer's pocket to the firm's bottom line?
        """
        
        logger.info(f"BlindExtractionAgent: Performing high-insight extraction for {company_name}...")
        
        if cached_content:
            result = self.client.generate_structured_content([prompt_text], BlindQualitativeExtractionSchema, cached_content=cached_content)
        else:
            result = self.client.generate_structured_content([prompt_text, gemini_file], BlindQualitativeExtractionSchema)
            
        if not result:
            logger.error("BlindExtractionAgent failed to return a valid schema.")
        return result

class BlindEvaluationAgent:
    def __init__(self, client: GeminiClient):
        self.client = client
        
    def evaluate(self, extraction_data: BlindQualitativeExtractionSchema) -> BlindQualitativeEvaluationSchema:
        """Pass Two: Evaluates the structural quality using strategic synthesis."""
        
        prompt_text = f"""
        You are an elite Chief Investment Officer specializing in structural business analysis.
        Evaluate the following anonymized business profile. Apply strategic frameworks (Porter's 5 Forces, Helmer's 7 Powers) with a focus on durability and scalability.
        
        DATA FOR EVALUATION:
        {extraction_data.model_dump_json(indent=2)}
        
        EVALUATION FRAMEWORKS:
        1. **The Primary Constraint**: In the Porter's analysis, identify the ONE force that acts as the primary constraint on long-term profitability.
        2. **Moat Sustainability**: Evaluate the durability of the structural advantages over a 10-year horizon. Be specific about competitive threats and potential for commoditization.
        3. **Talent & Culture Context**: If the business is human-capital intensive, evaluate the sustainability of its talent model and any brain-drain risks.
        4. **Operational Tensions**: Identify any internal contradictions or strategic trade-offs in the model.
        5. **Balanced Perspective**: Refine the **Industry Context**, **Strategic Maneuvers**, and **Future Catalysts** from the extraction phase, adding your objective strategic evaluation.
        
        GOAL:
        Write a vivid, insightful, and balanced assessment that avoids corporate clichés.
        """
        
        logger.info("BlindEvaluationAgent: Performing strategic synthesis evaluation...")
        
        result = self.client.generate_structured_content([prompt_text], BlindQualitativeEvaluationSchema)
        
        if not result:
            logger.error("BlindEvaluationAgent failed to return a valid schema.")
        return result
