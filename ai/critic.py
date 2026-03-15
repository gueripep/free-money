from ai.schemas import TableExtractionSchema, FinancialYearData
from core.config import setup_logging
from typing import Tuple, List

logger = setup_logging("critic")

class CriticValidator:
    """A deterministic, non-LLM validation layer for extracted financial data."""
    
    TOLERANCE = 10000.0 # Allow for rounding errors in large-scale reports (e.g. 1000 Yen in billions)
    
    def validate(self, data: TableExtractionSchema) -> Tuple[bool, List[str]]:
        """Runs the full suite of accounting checks on the extracted data."""
        self.errors = []
        
        logger.info(f"CriticValidator inspecting {len(data.fiscal_years_extracted)} years for {data.company_name} (Tolerance: {self.TOLERANCE})...")
        
        for year_data in data.fiscal_years_extracted:
            self._validate_balance_sheet_equation(year_data)
            self._validate_gross_profit(year_data)
            self._validate_current_assets_subtotals(year_data)
            
        is_valid = len(self.errors) == 0
        if not is_valid:
             logger.warning(f"CriticValidator failed with {len(self.errors)} errors: {self.errors}")
        else:
             logger.info("CriticValidator: All mathematical checks passed.")
             
        return is_valid, self.errors

    def _validate_balance_sheet_equation(self, year_data: FinancialYearData):
        """Fundamental check: Assets = Liabilities + Equity."""
        # We need all three to do the check
        if year_data.total_assets is not None and year_data.total_liabilities is not None and year_data.total_equity is not None:
            calculated_assets = year_data.total_liabilities + year_data.total_equity
            
            # Using tolerance for rounding
            if abs(year_data.total_assets - calculated_assets) > self.TOLERANCE: 
                self.errors.append(
                    f"Year {year_data.year} Balance Sheet Error: Reported Assets ({year_data.total_assets}) "
                    f"!= Liabilities ({year_data.total_liabilities}) + Equity ({year_data.total_equity}). Calculated: {calculated_assets}."
                )

    def _validate_gross_profit(self, year_data: FinancialYearData):
        """Check: Revenue - COGS = Gross Profit"""
        if year_data.total_revenue is not None and year_data.cogs is not None and year_data.gross_profit is not None:
            calculated_gp = year_data.total_revenue - year_data.cogs
            if abs(year_data.gross_profit - calculated_gp) > self.TOLERANCE:
                 self.errors.append(
                    f"Year {year_data.year} Income Statement Error: Reported Gross Profit ({year_data.gross_profit}) "
                    f"!= Revenue ({year_data.total_revenue}) - COGS ({year_data.cogs}). Calculated: {calculated_gp}."
                )

    def _validate_current_assets_subtotals(self, year_data: FinancialYearData):
         """Check: Sum of extracted current asset items <= Total Current Assets"""
         if year_data.current_assets is not None:
             # Sum whatever granular fields we have
             components = [
                 year_data.cash_and_equivalents or 0,
                 year_data.accounts_receivable or 0,
                 year_data.inventory or 0
             ]
             subtotal = sum(components)
             
             # The sum of specific components shouldn't be larger than the total (with tolerance)
             if subtotal > year_data.current_assets + self.TOLERANCE:
                  self.errors.append(
                    f"Year {year_data.year} Current Assets Subtotal Error: Sum of cash/receivables/inventory ({subtotal}) "
                    f"is greater than reported Total Current Assets ({year_data.current_assets})."
                )
