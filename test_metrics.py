import sys
import os
sys.path.append(os.path.abspath('.'))
from pipeline.02_fetch_financials import get_financial_metrics
metrics = get_financial_metrics('ALBKK.PA')
print("Shares CAGR:", metrics.get('shares_outstanding_cagr'))
print("EBITDA Margin Exp:", metrics.get('ebitda_margin_expansion'))
