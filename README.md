# Sale Incentive

Calculates sales incentives from a CSV of sales records.

## Run
All input files must be in `data/` (the program refuses files elsewhere):
`data/rates.xlsx` (commission rates) and the sales export (`.txt` / `.csv` / `.xlsx`).
```
pip install -r requirements.txt
python make_rates_template.py        # first time only: creates data/rates.xlsx
python incentive.py IC3051-3.txt     # file name inside data/
```

## Web app — multi-company (recommended)
```
pip install -r requirements-web.txt
APP_PASSWORD=... streamlit run app.py      # http://localhost:8501
```
1. **Select company** — CBG / SAS / CM / DAP UV / SC (Silkcut uses the CBG rules).
2. **Check / edit the rate tables** (defaults pre-filled). Edits apply to this run;
   "บันทึกเป็นค่า default" saves them to `data/company_settings/<company>.json` (not in git).
3. **Upload the sales export**, untick salespeople who are not eligible.
4. **Calculate → download** `incentive_<company>_<year>.xlsx` (Sale Summary, Raw Data, Settings = rates used).

| Company | Rule |
|---|---|
| CBG | Type (NC/OCNP/OCOP) × margin tier, New Product flat rate (see below) |
| SAS | Material (P-class ≠ GTP) 0.01% · Machine (GTP) 1% · Machine to BU BDI 0.8% |
| CM | Material (P-line not 5xx) 0.40% when Saleman × P-line × month sales ≥ 70% of FSA · Machine Standard (5XXXX01) / Project (5XXXX02): tier % by Saleman's monthly machine sales, applied to the whole amount · machine below MIN Price without MD approval = 0 and not counted |
| DAP UV | Flat 0.5% |
| SC (Silkcut) | Same rules as CBG (own rate tables / saved defaults) |

Common: rows without a Saleman (`NO SALEMAN`) and non-eligible salespeople (`NOT ELIGIBLE`) get 0.
SAS / CM / DAP UV also use the `payment` columns in `config.yaml` (paid date, MD approval): unpaid rows
= `UNPAID`; Payout Month = Invoice + 4 months (materials) or paid date (machines: before the 20th →
same month, otherwise next month). If the paid-date column is missing, all invoices are counted and a
warning is shown.

## Configure
1. **`data/rates.xlsx`** — create it with `python make_rates_template.py`, then fill in every yellow cell before running (values can differ per company):
   - `TYPE/MARGIN` table: commission % for each Type × Tier (LOW / MID / HIGH)
   - `MARGIN TYPE` table: MIN margin of each Tier. A row gets the highest Tier whose MIN it
     reaches (margin ≥ MIN). Below the lowest MIN = `BELOW LOW`, no commission.
   - `New Product` sheet: Item No. → flat Commission % (any Type). Add rows as needed.
   The program refuses to run if any yellow cell is empty or two MINs are equal.
   Older rates files: add the sheet with `python make_rates_template.py --add-new-product`.

   **Commission Tier per row** (checked in this order):
   1. `NO COMMISSION` — Item No. USDB or Actual Cost = 0
   2. `BELOW LOW` — margin below the lowest MIN
   3. `NEW PRODUCT` — Item No. listed in the New Product sheet → flat rate
   4. `LOW` / `MID` / `HIGH` — Type × margin tier rate
2. **`config.yaml`** — column names (margin column = `PGROSS`) and `margin_type`
   (`percent` = 25 means 25%, `ratio` = 0.25, `amount` = gross profit in THB).

| Type | Rule |
|---|---|
| NC | Customer with no bills in the previous 2 calendar years |
| OCNP | Existing customer, within 2 years of the customer's **first** purchase of that P-line (first buy 15 Dec 2025 → OCNP until 14 Dec 2027). History = the whole file, so the export must go back far enough |
| OCOP | Existing customer, existing P-line |

Rows with `Item No.` = USDB or `Actual Cost(THB)` = 0 get no commission (Tier `NO COMMISSION`); they still count as purchase history. Configure in `no_commission`.

Margin is evaluated per row. Amounts are before VAT (`Net Price (THB)`).
Only the latest year in the file is calculated; the 2 years before are reference only.

Result: `output/incentive_<year>.xlsx` with 2 sheets — **Sale Summary** (commission per Saleman by month) and
**Raw Data** (original rows of that year **without margin/cost columns** + Month, Year, Type,
Commission Tier, Calculated Commission %, Commission (THB)). Sales staff see only the Tier, never the actual margin.

## Data
Put real sales files (CSV or Excel .xlsx) in `data/`. They are git-ignored and never committed.
