# Sale Incentive

Calculates sales incentives from a CSV of sales records.

## Run
```
pip install -r requirements.txt
python incentive.py data/sample_sales.csv
```

## Configure
1. **`rates.xlsx`** — fill in every yellow cell before running (values can differ per company):
   - `TYPE/MARGIN` table: commission % for each Type × Tier (LOW / MID / HIGH)
   - `MARGIN TYPE` table: MIN margin of each Tier. A row gets the highest Tier whose MIN it
     reaches (margin ≥ MIN). Below the lowest MIN = `BELOW MIN`, no commission.
   The program refuses to run if any yellow cell is empty or two MINs are equal.
   Recreate a blank copy with `python make_rates_template.py`.
2. **`config.yaml`** — column names (margin column = `PGROSS`) and `margin_type`
   (`percent` = 25 means 25%, `ratio` = 0.25, `amount` = gross profit in THB).

| Type | Rule |
|---|---|
| NC | Customer with no bills in the previous 2 calendar years |
| OCNP | Existing customer, P-line not bought in the previous 2 years |
| OCOP | Existing customer, existing P-line |

Margin is evaluated per row. Amounts are before VAT (`Net Price (THB)`).
Only the latest year in the file is calculated; the 2 years before are reference only.

Results: `output/sale_summary_<year>.csv` (incentive per Saleman by month) and
`output/raw_data_<year>.csv` (original rows of that year **without the margin column** + Type,
Margin Tier, Calculated Commission %, Commission (THB)). Sales staff see only the Tier, never the actual margin.

## Data
Put real sales files (CSV or Excel .xlsx) in `data/`. They are git-ignored and never committed.
