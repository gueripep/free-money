import os
import sys
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

# Ensure script runs with the correct path relative to the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.database as db
from core.config import DATA_DIR, setup_logging
from ai.gemini_client import GeminiClient
from ai.prompts import get_tier_list_comparison_prompt

logger = setup_logging("rank_candidates")

def winsorize_zscore(series, cap=3.0):
    """Compute z-scores and cap at ±cap to prevent outlier domination.
    
    A single extreme value (e.g., ROIIC of 389% from a difference/difference
    artifact) can generate a z-score of 5+ and single-handedly dominate the
    composite score. Capping at ±3.0 ensures elite metrics still score high
    but cannot overpower all other dimensions combined.
    """
    z = (series - series.mean()) / (series.std() + 1e-6)
    return z.clip(-cap, cap)


def load_methodology() -> str:
    """Loads the tier list methodology text."""
    # Using a condensed version of the methodology text for the AI context.
    return """
The Calculus of Outperformance: Multi-Factor Weighted Scoring Model
- Capital Efficiency (30%): ROIIC, 3GP Score, FCF Yield.
- Moat & Margin Durability (25%): ROIC Decay, Gross Margin Stability, SG&A Efficiency.
- Growth-Adjusted Valuation (20%): EV/Sales/Growth, EV/GP.
- Downside & Forensic Risk (15%): Altman Z-Score, Accruals Ratio, Cash Runway, Share Dilution/Buybacks.
- Market Runway (10%): Market Penetration Rate, TAM/SOM.

Notes:
- All z-scores are winsorized (capped at ±3.0 std dev) to prevent outlier domination.
- Companies in Altman Z-Score distress zone (<1.8) are hard-capped below S-Tier.
"""

def process_tier_list(gemini_client: Optional[GeminiClient] = None):
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
        'accruals_ratio', 'cash_runway_months', 'shares_outstanding_cagr'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- Dimension Scoring (Winsorized Z-Scores, capped at ±3.0) ---
    logger.info("Computing Dimension Z-Scores (winsorized at ±3.0)...")
    
    # 1. Moat & Margin (25%)
    # Higher is better for expansion, lower is better for decay/stability/sga
    df['score_moat'] = (
        winsorize_zscore(df['ebitda_margin_expansion']) -
        winsorize_zscore(df['roic_decay_rate']) -
        winsorize_zscore(df['gross_margin_stability']) -
        winsorize_zscore(df['sga_efficiency_delta'])
    )

    # 2. Capital Efficiency (30%)
    df['score_efficiency'] = (
        winsorize_zscore(df['roiic']) +
        winsorize_zscore(df['three_gp_score'])
    )

    # 3. Downside & Forensic Risk (15%)
    # Higher is better for altman/runway, lower is better for accruals/dilution
    df['score_risk'] = (
        winsorize_zscore(df['altman_z_score']) +
        winsorize_zscore(df['cash_runway_months']) -
        winsorize_zscore(df['accruals_ratio']) -
        winsorize_zscore(df['shares_outstanding_cagr'])  # Penalize dilution, reward buybacks
    )

    # 4. Growth-Adjusted Valuation (20%) & 5. Market Runway (10%)
    # Simplified proxy: High Growth + Low MCap/Valuation
    df['revenue_growth'] = pd.to_numeric(df['revenue_growth'], errors='coerce').fillna(0)
    df['inorganic_growth_ratio'] = pd.to_numeric(df['inorganic_growth_ratio'], errors='coerce').fillna(0)
    
    # Penalty: Discount the revenue growth based on how much was bought
    # ONLY penalize if they are a "Dilutive" acquirer. Compounders get a pass.
    def get_organic_growth(row):
        rev = row['revenue_growth']
        if row.get('is_acquirer') == 1 and row.get('acquirer_type') == 'Dilutive':
            ratio = min(float(row.get('inorganic_growth_ratio', 0)), 1.0)
            return rev * (1 - ratio)
        return rev
        
    df['organic_revenue_growth'] = df.apply(get_organic_growth, axis=1)
    
    df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce').fillna(1e12)
    df['log_mcap'] = np.log(df['market_cap'])
    df['score_growth_val'] = (
        winsorize_zscore(df['organic_revenue_growth']) -
        winsorize_zscore(df['log_mcap'])
    )

    # --- Weighted Composite Score ---
    df['composite_score'] = (
        0.25 * df['score_moat'] +
        0.30 * df['score_efficiency'] +
        0.15 * df['score_risk'] +
        0.30 * df['score_growth_val']  # Combining last two for simplicity in proxy logic
    )

    # --- Distress Circuit-Breaker ---
    # Companies in Altman Z-Score distress zone (<1.8) are hard-capped below S-Tier.
    # Even with winsorized z-scores, a near-bankrupt company should never reach S-tier
    # just because one ratio (e.g., ROIIC from a diff/diff artifact) is extreme.
    mean_cs = df['composite_score'].mean()
    std_cs = df['composite_score'].std()
    s_tier_threshold = mean_cs + 1.2 * std_cs  # S-tier entry point
    a_tier_cap = mean_cs + 0.5 * std_cs         # Cap distressed at top of A-tier
    
    distress_mask = df['altman_z_score'] < 1.8
    distressed_count = distress_mask.sum()
    if distressed_count > 0:
        df.loc[distress_mask, 'composite_score'] = df.loc[distress_mask, 'composite_score'].clip(upper=a_tier_cap)
        logger.info(f"Distress circuit-breaker applied to {distressed_count} companies (Altman Z < 1.8, capped below S-Tier)")

    # Sort candidates
    df = df.sort_values(by='composite_score', ascending=False)
    
    # Prepare Cohort Summary for LLM
    logger.info("Preparing Mathematical Cohort Summary for Stage 2 Synthesis...")
    
    readable_cols = ['name', 'ticker', 'composite_score', 'score_moat', 'score_efficiency', 'score_risk', 'score_growth_val', 'roiic', 'three_gp_score', 'altman_z_score', 'revenue_growth', 'cash_runway_months', 'shares_outstanding_cagr']
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
    
    gemini = gemini_client or GeminiClient()
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
