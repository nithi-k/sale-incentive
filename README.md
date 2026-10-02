# Sale Incentive

Calculates sales incentives from a CSV of sales records.

## Run
```
pip install -r requirements.txt
python incentive.py data/sample_sales.csv
```
Results: `output/sale_summary_<year>.csv` (incentive per Saleman by month) and `output/raw_data_<year>.csv` (original rows of that year + `Type` column: NC / OCNP / OCOP).

## Configure
Edit `config.yaml` to set the CSV column names, lookback years and rates.

| Category | Rule | Rate |
|---|---|---|
| NC | Customer with no bills in the previous 2 calendar years | 3% |
| OCNP | Existing customer, Pline not bought in the previous 2 years | 1% |
| OCOP | Existing customer, existing Pline | 0.5% |

Amounts are before VAT. Use `--year 2026` to pick the year (default: latest year in the file).

## Data
Put real sales files (CSV or Excel .xlsx) in `data/`. They are git-ignored and never committed.
