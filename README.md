# Sale Incentive

Calculates sales incentives from a CSV of sales records.

## Run
```
pip install -r requirements.txt
python incentive.py data/sample_sales.csv
```
Results are written to `output/incentive.csv`.

## Configure
Edit `config.yaml` to set the CSV column names and incentive tiers.

## Data
Put real sales CSVs in `data/`. They are git-ignored and never committed.
