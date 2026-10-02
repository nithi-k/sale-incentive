"""Sales incentive calculator.

Usage: python incentive.py data/sales.csv [--config config.yaml] [--out output/incentive.csv]
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import yaml


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rate_for(total, tiers):
    rate = 0.0
    for tier in sorted(tiers, key=lambda t: t["min"]):
        if total >= tier["min"]:
            rate = tier["rate"]
    return rate


def calculate(sales_csv, cfg):
    cols = cfg["columns"]
    totals = defaultdict(float)
    with open(sales_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            amount = float(str(row[cols["amount"]]).replace(",", "") or 0)
            totals[row[cols["salesperson"]].strip()] += amount
    results = []
    for person, total in sorted(totals.items()):
        rate = rate_for(total, cfg["tiers"])
        results.append({"salesperson": person, "total_sales": round(total, 2),
                        "rate": rate, "incentive": round(total * rate, 2)})
    return results


def main():
    p = argparse.ArgumentParser(description="Calculate sales incentives from a CSV")
    p.add_argument("sales_csv")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--out", default="output/incentive.csv")
    a = p.parse_args()
    results = calculate(a.sales_csv, load_config(a.config))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["salesperson", "total_sales", "rate", "incentive"])
        w.writeheader()
        w.writerows(results)
    for r in results:
        print(f"{r['salesperson']:<15} {r['total_sales']:>12,.2f}  {r['rate']:.1%}  {r['incentive']:>10,.2f}")
    print(f"\nSaved to {a.out}")


if __name__ == "__main__":
    main()
