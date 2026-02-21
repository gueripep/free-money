import os
import sys
import pandas as pd
import numpy as np

# Ensure script runs with the correct path relative to the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.database as db
from core.config import DATA_DIR, setup_logging
from ai.gemini_client import GeminiClient
from ai.prompts import get_tier_list_comparison_prompt

logger = setup_logging("rank_candidates")

def load_methodology() -> str:
    """Loads the tier list methodology text."""
    # Using a condensed version of the methodology text for the AI context.
    return """
The Calculus of Outperformance: Multi-Factor Weighted Scoring Model
- Capital Efficiency (30%): ROIIC, 3GP Score, FCF Yield.
- Moat & Margin Durability (25%): ROIC Decay, Gross Margin Stability, SG&A Efficiency.
- Growth-Adjusted Valuation (20%): EV/Sales/Growth, EV/GP.
- Downside & Forensic Risk (15%): Altman Z-Score, Accruals Ratio, Cash Runway.
- Market Runway (10%): Market Penetration Rate, TAM/SOM.
"""

def process_tier_list():
    logger.info("Starting Tier List Pipeline (Mathematical Ranking)")
    
    all_candidates = db.get_all_candidates()
    
    if not all_candidates:
        logger.error("No candidates found in the database. Run the fetch/enrich pipelines first.")
        return
        
    logger.info(f"Found {len(all_candidates)} candidates ready for Mathematical Ranking.")
    
    # Create DataFrame
    df = pd.DataFrame(all_candidates)
    
    # Pre-processing: Convert numeric columns and handle "DATA NOT FOUND"
    numeric_cols = [
        'roic_decay_rate', 'gross_margin_stability', 'sga_efficiency_delta',
        'ebitda_margin_expansion', 'roiic', 'three_gp_score', 'altman_z_score',
        'accruals_ratio', 'cash_runway_months'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- Dimension Scoring (Calculation of Z-Scores) ---
    logger.info("Computing Dimension Z-Scores...")
    
    # 1. Moat & Margin (25%)
    # Higher is better for expansion, lower is better for decay/stability/sga
    df['score_moat'] = (
        (df['ebitda_margin_expansion'] - df['ebitda_margin_expansion'].mean()) / (df['ebitda_margin_expansion'].std() + 1e-6) -
        (df['roic_decay_rate'] - df['roic_decay_rate'].mean()) / (df['roic_decay_rate'].std() + 1e-6) -
        (df['gross_margin_stability'] - df['gross_margin_stability'].mean()) / (df['gross_margin_stability'].std() + 1e-6) -
        (df['sga_efficiency_delta'] - df['sga_efficiency_delta'].mean()) / (df['sga_efficiency_delta'].std() + 1e-6)
    )

    # 2. Capital Efficiency (30%)
    df['score_efficiency'] = (
        (df['roiic'] - df['roiic'].mean()) / (df['roiic'].std() + 1e-6) +
        (df['three_gp_score'] - df['three_gp_score'].mean()) / (df['three_gp_score'].std() + 1e-6)
    )

    # 3. Downside & Forensic Risk (15%)
    # Lower is better for accruals
    df['score_risk'] = (
        (df['altman_z_score'] - df['altman_z_score'].mean()) / (df['altman_z_score'].std() + 1e-6) +
        (df['cash_runway_months'] - df['cash_runway_months'].mean()) / (df['cash_runway_months'].std() + 1e-6) -
        (df['accruals_ratio'] - df['accruals_ratio'].mean()) / (df['accruals_ratio'].std() + 1e-6)
    )

    # 4. Growth-Adjusted Valuation (20%) & 5. Market Runway (10%)
    # Simplified proxy: High Growth + Low MCap/Valuation
    df['revenue_growth'] = pd.to_numeric(df['revenue_growth'], errors='coerce').fillna(0)
    df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce').fillna(1e12)
    df['log_mcap'] = np.log(df['market_cap'])
    df['score_growth_val'] = (
        (df['revenue_growth'] - df['revenue_growth'].mean()) / (df['revenue_growth'].std() + 1e-6) -
        (df['log_mcap'] - df['log_mcap'].mean()) / (df['log_mcap'].std() + 1e-6)
    )

    # --- Weighted Composite Score ---
    df['composite_score'] = (
        0.25 * df['score_moat'] +
        0.30 * df['score_efficiency'] +
        0.15 * df['score_risk'] +
        0.30 * df['score_growth_val']  # Combining last two for simplicity in proxy logic
    )

    # Sort candidates
    df = df.sort_values(by='composite_score', ascending=False)
    
    # Prepare Cohort Summary for LLM
    logger.info("Preparing Mathematical Cohort Summary for Stage 2 Synthesis...")
    
    readable_cols = ['name', 'ticker', 'composite_score', 'roiic', 'three_gp_score', 'altman_z_score', 'revenue_growth', 'cash_runway_months']
    df_summary = df[readable_cols].copy()
    
    # Map raw scores to intuitive tiers for the LLM
    def assign_tier(val, mean, std):
        if val > mean + 1.2 * std: return "🏆 S-TIER"
        if val > mean + 0.5 * std: return "🥇 A-TIER"
        if val > mean - 0.5 * std: return "🥈 B-TIER"
        if val > mean - 1.2 * std: return "🥉 C-TIER"
        return "📉 RED FLAG"

    mean_s = df['composite_score'].mean()
    std_s = df['composite_score'].std()
    df_summary['Mathematical_Tier'] = df['composite_score'].apply(lambda x: assign_tier(x, mean_s, std_s))
    
    # --- Persistence: Save results to DB ---
    logger.info("Persisting mathematical rankings to database...")
    for _, row in df.iterrows():
        tier = assign_tier(row['composite_score'], mean_s, std_s)
        db.update_ranking_data(row['isin'], float(row['composite_score']), tier)
    
    cohort_text = "### GLOBAL QUANTITATIVE RANKING (Pre-Calculated in Python)\n\n"
    cohort_text += df_summary.to_markdown(index=False)
    
    # Stage 2: Synthesis and Tier List Ranking
    logger.info("=== STAGE 2: HIERARCHICAL TIER LIST RANKING (Synthesis) ===")
    
    gemini = GeminiClient()
    methodology = load_methodology()
    
    ranking_prompt = get_tier_list_comparison_prompt(cohort_text, methodology)
    final_ranking_md = gemini.generate_tier_list_text(ranking_prompt)
    
    if final_ranking_md:
        findings_dir = os.path.join(DATA_DIR, "findings")
        os.makedirs(findings_dir, exist_ok=True)
        tier_list_path = os.path.join(findings_dir, "TIER_LIST_RANKING_MATH.md")
        
        with open(tier_list_path, "w", encoding="utf-8") as f:
            f.write(final_ranking_md)
            
        logger.info(f"Math-Based Rankings successfully generated and saved to {tier_list_path}")
    else:
        logger.error("Failed to generate final tier list ranking.")

if __name__ == "__main__":
    process_tier_list()
