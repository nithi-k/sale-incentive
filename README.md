# Sale Incentive

Calculates sales incentives from a CSV of sales records.

## Run
```
pip install -r requirements.txt
python incentive.py data/sample_sales.csv
```

## Configure
1. **`rates.xlsx`** — fill in every yellow cell before running: margin band limits
   ("Margin ตั้งแต่ (≥)" / "Margin น้อยกว่า (<)", blank = no limit at the bottom/top band)
   and the incentive rate for each Type × margin band. The program refuses to run if any
   required cell is empty. Recreate a blank copy with `python make_rates_template.py`.
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
`output/raw_data_<year>.csv` (original rows of that year + Type, Margin Band, Rate, Incentive).

## Data
Put real sales files (CSV or Excel .xlsx) in `data/`. They are git-ignored and never committed.
