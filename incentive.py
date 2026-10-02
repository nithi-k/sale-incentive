"""คำนวณ Sales Incentive จากไฟล์ CSV ยอดขาย

ประเภทยอดขาย (ปีที่คำนวณ = Y, เช็คย้อนหลังปี Y-1 ถึง Y-lookback):
  NC   ลูกค้าใหม่              : ลูกค้าไม่มีบิลเลยในช่วงย้อนหลัง
  OCNP ลูกค้าเก่า + สินค้าใหม่ : ลูกค้าเก่า แต่ไม่เคยซื้อ Pline นี้ในช่วงย้อนหลัง
  OCOP ลูกค้าเก่า + สินค้าเก่า : นอกเหนือจากนั้น

Usage: python incentive.py data/sales.csv (หรือ .xlsx) [--year 2026] [--config config.yaml]
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
        v = r[cols["date"]]
        return v if isinstance(v, datetime) else parse_date(cell_str(v))
    return datetime(int(float(r[cols["year"]])), int(float(r[cols["month"]])), int(float(r[cols["day"]])))


def cell_str(v):
    """แปลงค่าจาก CSV/Excel เป็นข้อความ (เช่น 530011.0 -> '530011')"""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def read_table(path):
    """อ่าน CSV หรือ Excel (.xlsx) คืนค่า (header, list ของ dict)"""
    if Path(path).suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = [cell_str(h) for h in next(it)]
        rows = [dict(zip(header, r)) for r in it if any(v is not None for v in r)]
        wb.close()
        return header, rows
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def load_sales(path, cols):
    header, raw_rows = read_table(path)
    rows = []
    for r in raw_rows:
        rows.append({
            "raw": r,
            "date": row_date(r, cols),
            "salesperson": cell_str(r[cols["salesperson"]]),
            "customer": cell_str(r[cols["customer"]]),
            "pline": cell_str(r[cols["pline"]]),
            "amount": float(cell_str(r[cols["amount"]]).replace(",", "") or 0),
        })
    return rows, header


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
    rows, header = load_sales(a.sales_csv, cfg["columns"])
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

    out = Path(a.outdir)
    clear_output(out)

    # File 2: raw data ของปีที่คำนวณ + คอลัมน์ Type
    with open(out / f"raw_data_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(header) + ["Type"])
        w.writeheader()
        for d in detail:
            w.writerow({**d["raw"], "Type": d["category"]})

    # File 1: Sale Summary — incentive ต่อ Saleman แยกรายเดือน
    months = list(range(1, 13))
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = defaultdict(lambda: [0.0] * 12)
    for d in detail:
        monthly[d["salesperson"]][d["date"].month - 1] += d["incentive"]
    names = sorted(monthly)
    col_total = [sum(monthly[n][m - 1] for n in names) for m in months]
    with open(out / f"sale_summary_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Saleman"] + month_names + ["Total"])
        for n in names:
            w.writerow([n] + [round(v, 2) for v in monthly[n]] + [round(sum(monthly[n]), 2)])
        w.writerow(["Total"] + [round(v, 2) for v in col_total] + [round(sum(col_total), 2)])

    print(f"Incentive ปี {year} (เช็คย้อนหลังปี {year - lookback}-{year - 1})\n")
    print(f"{'Saleman':<10}" + "".join(f"{m:>9}" for m in month_names) + f"{'Total':>11}")
    for n in names + ["Total"]:
        vals = col_total if n == "Total" else monthly[n]
        print(f"{n:<10}" + "".join(f"{v:>9,.0f}" for v in vals) + f"{sum(vals):>11,.2f}")
    print(f"\nบันทึกไฟล์ที่ {out}/")


if __name__ == "__main__":
    main()
