"""คำนวณ Sales Incentive จากไฟล์ CSV ยอดขาย

ประเภทยอดขาย (ปีที่คำนวณ = Y, เช็คย้อนหลังปี Y-1 ถึง Y-lookback):
  NC   ลูกค้าใหม่              : ลูกค้าไม่มีบิลเลยในช่วงย้อนหลัง
  OCNP ลูกค้าเก่า + สินค้าใหม่ : ลูกค้าเก่า แต่ไม่เคยซื้อ Pline นี้ในช่วงย้อนหลัง
  OCOP ลูกค้าเก่า + สินค้าเก่า : นอกเหนือจากนั้น

Usage: python incentive.py data/sales.csv [--year 2026] [--config config.yaml]
"""
import argparse
import csv
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_date(s):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"อ่านวันที่ไม่ได้: {s!r}")


def row_date(r, cols):
    if "date" in cols:
        return parse_date(r[cols["date"]])
    return datetime(int(r[cols["year"]]), int(r[cols["month"]]), int(r[cols["day"]]))


def load_sales(path, cols):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "date": row_date(r, cols),
                "salesperson": r[cols["salesperson"]].strip(),
                "customer": r[cols["customer"]].strip(),
                "pline": r[cols["pline"]].strip(),
                "amount": float(str(r[cols["amount"]]).replace(",", "") or 0),
            })
    return rows


def classify(rows, year, lookback):
    """เพิ่ม category ให้ทุกบรรทัดของปี `year`"""
    hist_years = set(range(year - lookback, year))
    hist_customers, hist_cust_pline = set(), set()
    for r in rows:
        if r["date"].year in hist_years:
            hist_customers.add(r["customer"])
            hist_cust_pline.add((r["customer"], r["pline"]))
    out = []
    for r in rows:
        if r["date"].year != year:
            continue
        if r["customer"] not in hist_customers:
            cat = "NC"
        elif (r["customer"], r["pline"]) not in hist_cust_pline:
            cat = "OCNP"
        else:
            cat = "OCOP"
        out.append({**r, "category": cat})
    return out


def clear_output(out):
    """ลบทุกอย่างในโฟลเดอร์ output ก่อนรัน (กันลบโฟลเดอร์โปรเจกต์หรือโฟลเดอร์แม่โดยไม่ตั้งใจ)"""
    out = out.resolve()
    cwd = Path.cwd().resolve()
    if out == cwd or out in cwd.parents or out == Path.home().resolve():
        raise SystemExit(f"ไม่ลบ {out} — outdir ต้องเป็นโฟลเดอร์ย่อยสำหรับผลลัพธ์เท่านั้น")
    if out.exists():
        for item in out.iterdir():
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    out.mkdir(parents=True, exist_ok=True)


def main():
    p = argparse.ArgumentParser(description="คำนวณ Sales Incentive")
    p.add_argument("sales_csv")
    p.add_argument("--year", type=int, help="ปีที่คำนวณ (ค่าเริ่มต้น = ปีล่าสุดในไฟล์)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--outdir", default="output")
    a = p.parse_args()

    cfg = load_config(a.config)
    rows = load_sales(a.sales_csv, cfg["columns"])
    excluded = set(cfg.get("exclude_plines") or [])
    rows = [r for r in rows if r["pline"] not in excluded]
    if not rows:
        print("ไม่มียอดขายให้คำนวณ (หลังตัด P-line ที่ยกเว้น)")
        return
    year = a.year or max(r["date"].year for r in rows)
    lookback = cfg.get("lookback_years", 2)
    years_in_file = {r["date"].year for r in rows}
    missing = [y for y in range(year - lookback, year) if y not in years_in_file]
    if missing:
        print(f"⚠️  ไม่มีข้อมูลปี {missing} ในไฟล์ — ลูกค้าอาจถูกนับเป็น NC เกินจริง")

    rates = cfg["rates"]
    detail = classify(rows, year, lookback)
    for d in detail:
        d["rate"] = rates[d["category"]]
        d["incentive"] = round(d["amount"] * d["rate"], 2)

    # สรุปต่อเซลส์
    cats = ["NC", "OCNP", "OCOP"]
    summary = defaultdict(lambda: {**{f"{c}_sales": 0.0 for c in cats}, "incentive": 0.0})
    for d in detail:
        s = summary[d["salesperson"]]
        s[f"{d['category']}_sales"] += d["amount"]
        s["incentive"] += d["incentive"]

    out = Path(a.outdir)
    clear_output(out)
    with open(out / f"incentive_detail_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "salesperson", "customer", "pline", "amount", "category", "rate", "incentive"])
        for d in sorted(detail, key=lambda x: (x["salesperson"], x["date"])):
            w.writerow([d["date"].strftime("%Y-%m-%d"), d["salesperson"], d["customer"], d["pline"],
                        d["amount"], d["category"], d["rate"], d["incentive"]])
    with open(out / f"incentive_summary_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["salesperson"] + [f"{c}_sales" for c in cats] + ["total_sales", "incentive"])
        for name, s in sorted(summary.items()):
            total = sum(s[f"{c}_sales"] for c in cats)
            w.writerow([name] + [round(s[f"{c}_sales"], 2) for c in cats] + [round(total, 2), round(s["incentive"], 2)])

    print(f"Incentive ปี {year} (เช็คย้อนหลังปี {year - lookback}-{year - 1})\n")
    print(f"{'Sales':<12}{'NC':>12}{'OCNP':>12}{'OCOP':>12}{'Incentive':>12}")
    for name, s in sorted(summary.items()):
        print(f"{name:<12}" + "".join(f"{s[c + '_sales']:>12,.0f}" for c in cats) + f"{s['incentive']:>12,.2f}")
    print(f"\nบันทึกไฟล์ที่ {out}/")


if __name__ == "__main__":
    main()
