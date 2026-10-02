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
            "margin_raw": cell_str(r.get(cols["margin"])) if "margin" in cols else "",
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


CATEGORIES = ["OCOP", "OCNP", "NC"]


def load_rates(path):
    """อ่าน rates.xlsx: ช่วง Margin (ตั้งแต่ ≥ / น้อยกว่า <) และอัตราของแต่ละ Type
    คืนค่า list ของ band: {label, lo, hi, rates{Type: rate}}"""
    import openpyxl
    if not Path(path).exists():
        raise SystemExit(f"ไม่พบไฟล์อัตรา {path} — สร้างด้วย: python make_rates_template.py")
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    # หาแถวตามป้ายในคอลัมน์ A
    row_of = {}
    for r in range(1, ws.max_row + 1):
        v = cell_str(ws.cell(row=r, column=1).value)
        if v:
            row_of[v] = r
    label_row = row_of.get("TYPE/MARGIN")
    lo_row = next((r for k, r in row_of.items() if k.startswith("Margin") and "≥" in k), None)
    hi_row = next((r for k, r in row_of.items() if k.startswith("Margin") and "<" in k), None)
    if not all([label_row, lo_row, hi_row] + [row_of.get(c) for c in CATEGORIES]):
        raise SystemExit(f"รูปแบบ {path} ไม่ถูกต้อง — สร้างใหม่ด้วย make_rates_template.py")

    cols = []
    c = 2
    while cell_str(ws.cell(row=label_row, column=c).value):
        cols.append(c)
        c += 1
    if not cols:
        raise SystemExit(f"{path}: ไม่มีช่วง Margin")

    def num(r, c):
        v = ws.cell(row=r, column=c).value
        if v is None or cell_str(v) == "":
            return None
        if isinstance(v, str):
            v = v.strip().rstrip("%")
            return float(v) / 100
        return float(v)

    errors, bands = [], []
    for i, c in enumerate(cols):
        col = ws.cell(row=label_row, column=c).column_letter
        label = cell_str(ws.cell(row=label_row, column=c).value)
        lo, hi = num(lo_row, c), num(hi_row, c)
        if lo is None and i > 0:
            errors.append(f"{col}{lo_row} (Margin ตั้งแต่ ของช่วง {label})")
        if hi is None and i < len(cols) - 1:
            errors.append(f"{col}{hi_row} (Margin น้อยกว่า ของช่วง {label})")
        rates = {}
        for cat in CATEGORIES:
            v = num(row_of[cat], c)
            if v is None:
                errors.append(f"{col}{row_of[cat]} ({cat} ช่วง {label})")
            rates[cat] = v
        bands.append({"label": label, "lo": lo, "hi": hi, "rates": rates})
    if errors:
        raise SystemExit(f"❌ กรอก {path} ยังไม่ครบ — ช่องที่ว่าง:\n  " + "\n  ".join(errors))
    for b in bands:
        if b["lo"] is not None and b["hi"] is not None and b["lo"] >= b["hi"]:
            raise SystemExit(f"❌ {path}: ช่วง {b['label']} — 'ตั้งแต่' ต้องน้อยกว่า 'น้อยกว่า'")
    return bands


def to_margin(raw, amount, mtype):
    """แปลงค่า margin ของแถวเป็นสัดส่วน (0.25 = 25%)"""
    if raw == "":
        return None
    v = float(raw.replace(",", "").rstrip("%"))
    if mtype == "percent":
        return v / 100
    if mtype == "amount":
        return v / amount if amount else None
    return v


def find_band(m, bands):
    hits = [b for b in bands if (b["lo"] is None or m >= b["lo"]) and (b["hi"] is None or m < b["hi"])]
    return hits


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

    bands = load_rates(cfg.get("rates_file", "rates.xlsx"))
    if "margin" not in cfg["columns"] or cfg["columns"]["margin"] not in header:
        raise SystemExit(f"❌ ไม่พบคอลัมน์ Margin '{cfg['columns'].get('margin')}' ในไฟล์ยอดขาย")
    mtype = cfg.get("margin_type", "percent")
    detail = classify(rows, year, lookback)
    problems = []
    for d in detail:
        m = to_margin(d["margin_raw"], d["amount"], mtype)
        hits = [] if m is None else find_band(m, bands)
        if len(hits) != 1:
            why = "ไม่มีค่า Margin" if m is None else (
                f"Margin {m:.2%} ไม่อยู่ในช่วงใดเลย" if not hits else f"Margin {m:.2%} ตรงหลายช่วง")
            problems.append(f"{d['date']:%Y-%m-%d} ลูกค้า {d['customer']} P-line {d['pline']}: {why}")
            continue
        d["margin"], d["band"] = m, hits[0]["label"]
        d["rate"] = hits[0]["rates"][d["category"]]
        d["incentive"] = round(d["amount"] * d["rate"], 2)
    if problems:
        raise SystemExit(f"❌ มี {len(problems)} แถวที่หาอัตราไม่ได้ (ตัวอย่าง):\n  " + "\n  ".join(problems[:10]))

    out = Path(a.outdir)
    clear_output(out)

    # File 2: raw data ของปีที่คำนวณ + Type / Margin Band / Rate / Incentive
    extra = ["Type", "Margin Band", "Rate", "Incentive"]
    with open(out / f"raw_data_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(header) + extra)
        w.writeheader()
        for d in detail:
            w.writerow({**d["raw"], "Type": d["category"], "Margin Band": d["band"],
                        "Rate": d["rate"], "Incentive": d["incentive"]})

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
