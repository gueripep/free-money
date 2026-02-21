import sqlite3
import json

def check_mdm():
    conn = sqlite3.connect('e:/Documents/Antigravity/free-money/data/stocks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Find MDM - name contains Maisons or ticker is MDM.PA
    cursor.execute("SELECT * FROM stocks WHERE ticker LIKE '%MDM%' OR name LIKE '%Maisons%'")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Ticker: {row['ticker']}")
        print(f"Name: {row['name']}")
        print(f"Market Cap: {row['market_cap']}")
        print(f"Composite Score: {row['composite_score']}")
        print(f"Mathematical Tier: {row['mathematical_tier']}")
        print(f"Gross Margins: {row['gross_margins']}")
        print(f"Operating Cash Flow: {row['operating_cash_flow']}")
        print(f"Revenue Growth: {row['revenue_growth']}")
        print(f"Altman Z-Score: {row['altman_z_score']}")
        print(f"Cash Runway: {row['cash_runway_months']}")
        print("-" * 20)
    conn.close()

if __name__ == "__main__":
    check_mdm()
