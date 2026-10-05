"""คำนวณ Sales Incentive จากไฟล์ CSV ยอดขาย

ประเภทยอดขาย (ปีที่คำนวณ = Y, เช็คย้อนหลังปี Y-1 ถึง Y-lookback):
  NC   ลูกค้าใหม่              : ลูกค้าไม่มีบิลเลยในช่วงย้อนหลัง
  OCNP ลูกค้าเก่า + สินค้าใหม่ : ลูกค้าเก่า แต่ไม่เคยซื้อ Pline นี้ในช่วงย้อนหลัง
  OCOP ลูกค้าเก่า + สินค้าเก่า : นอกเหนือจากนั้น

Usage: python incentive.py IC3051.txt   (ไฟล์ต้องอยู่ใน data/ — .txt / .csv / .xlsx) [--year 2026] [--config config.yaml]
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


def read_table(path, delimiter=None):
    """อ่าน Raw Text (.txt), CSV หรือ Excel (.xlsx) คืนค่า (header, list ของ dict)"""
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
        first = f.readline()
        f.seek(0)
        if not delimiter:
            delimiter = max(["|", "\t", ","], key=first.count)
        reader = csv.DictReader(f, delimiter=delimiter)
        header = [h.strip() for h in reader.fieldnames]
        reader.fieldnames = header
        return header, list(reader)


def load_sales(path, cols, delimiter=None):
    header, raw_rows = read_table(path, delimiter)
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
BELOW = "BELOW MIN"


def load_rates(path):
    """อ่าน rates.xlsx
    ตาราง 'TYPE/MARGIN': Commission % ของแต่ละ Type ในแต่ละ Tier
    ตาราง 'MARGIN TYPE' : MIN Margin ของแต่ละ Tier
    คืนค่า list ของ tier เรียงจาก MIN น้อยไปมาก: {name, min, rates{Type: rate}}"""
    import openpyxl
    if not Path(path).exists():
        raise SystemExit(f"ไม่พบไฟล์อัตรา {path} — สร้างด้วย: python make_rates_template.py")
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]

    def find(label):
        for row in ws.iter_rows():
            for c in row:
                if cell_str(c.value).upper() == label:
                    return c.row, c.column
        raise SystemExit(f"❌ {path}: ไม่พบหัวตาราง '{label}' — สร้างใหม่ด้วย make_rates_template.py")

    def num(r, c):
        v = ws.cell(row=r, column=c).value
        if v is None or cell_str(v) == "":
            return None
        if isinstance(v, str):
            return float(v.strip().rstrip("%")) / 100
        return float(v)

    def ref(r, c):
        return f"{ws.cell(row=r, column=c).column_letter}{r}"

    errors = []
    # ตาราง Commission %
    hr, hc = find("TYPE/MARGIN")
    tier_cols = {}
    c = hc + 1
    while cell_str(ws.cell(row=hr, column=c).value):
        tier_cols[cell_str(ws.cell(row=hr, column=c).value).upper()] = c
        c += 1
    type_rows = {}
    r = hr + 1
    while cell_str(ws.cell(row=r, column=hc).value):
        type_rows[cell_str(ws.cell(row=r, column=hc).value).upper()] = r
        r += 1
    missing_types = [t for t in CATEGORIES if t not in type_rows]
    if missing_types or not tier_cols:
        raise SystemExit(f"❌ {path}: ตาราง TYPE/MARGIN ต้องมีแถว {CATEGORIES} และมี Tier อย่างน้อย 1 ช่อง")

    # ตาราง MIN
    mr, mc = find("MARGIN TYPE")
    mins = {}
    r = mr + 1
    while cell_str(ws.cell(row=r, column=mc).value):
        name = cell_str(ws.cell(row=r, column=mc).value).upper()
        v = num(r, mc + 1)
        if v is None:
            errors.append(f"{ref(r, mc + 1)} (MIN ของ {name})")
        mins[name] = v
        r += 1

    tiers = []
    for name, c in tier_cols.items():
        if name not in mins:
            errors.append(f"ตาราง MARGIN TYPE ไม่มี Tier '{name}'")
        rates = {}
        for t in CATEGORIES:
            v = num(type_rows[t], c)
            if v is None:
                errors.append(f"{ref(type_rows[t], c)} ({t} / {name})")
            rates[t] = v
        tiers.append({"name": name, "min": mins.get(name), "rates": rates})
    if errors:
        raise SystemExit(f"❌ กรอก {path} ยังไม่ครบ:\n  " + "\n  ".join(errors))
    tiers.sort(key=lambda t: t["min"])
    for a, b in zip(tiers, tiers[1:]):
        if a["min"] == b["min"]:
            raise SystemExit(f"❌ {path}: MIN ของ {a['name']} และ {b['name']} ซ้ำกัน ({a['min']:.2%})")
    return tiers


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


def find_tier(m, tiers):
    """Tier ที่ MIN สูงสุดซึ่ง Margin ถึง; ต่ำกว่า MIN ต่ำสุด = None"""
    hit = None
    for t in tiers:
        if m >= t["min"]:
            hit = t
    return hit


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


DATA_DIR = Path("data")


def in_data(path, what):
    """บังคับให้ไฟล์ input อยู่ในโฟลเดอร์ data/ เท่านั้น (ใส่แค่ชื่อไฟล์ก็ได้)"""
    p = Path(path)
    if not p.is_absolute() and p.parts[:1] != ("data",):
        p = DATA_DIR / p
    data = DATA_DIR.resolve()
    rp = p.resolve()
    if data not in rp.parents:
        raise SystemExit(f"❌ {what} ต้องอยู่ในโฟลเดอร์ data/ เท่านั้น: {path}")
    if not rp.exists():
        raise SystemExit(f"❌ ไม่พบ{what}: {p}")
    return rp


def main():
    p = argparse.ArgumentParser(description="คำนวณ Sales Incentive")
    p.add_argument("sales_csv", help="ไฟล์ยอดขายในโฟลเดอร์ data/ (ใส่แค่ชื่อไฟล์ได้)")
    p.add_argument("--year", type=int, help="ปีที่คำนวณ (ค่าเริ่มต้น = ปีล่าสุดในไฟล์)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--outdir", default="output")
    a = p.parse_args()

    cfg = load_config(a.config)
    a.sales_csv = in_data(a.sales_csv, "ไฟล์ยอดขาย")
    rates_path = in_data(cfg.get("rates_file", "rates.xlsx"), "ไฟล์อัตรา (rates.xlsx)")
    rows, header = load_sales(a.sales_csv, cfg["columns"], cfg.get("delimiter"))
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

    tiers = load_rates(rates_path)
    margin_col = cfg["columns"].get("margin")
    if not margin_col or margin_col not in header:
        raise SystemExit(f"❌ ไม่พบคอลัมน์ Margin '{margin_col}' ในไฟล์ยอดขาย")
    mtype = cfg.get("margin_type", "percent")
    detail = classify(rows, year, lookback)
    problems = []
    for d in detail:
        m = to_margin(d["margin_raw"], d["amount"], mtype)
        if m is None:
            problems.append(f"{d['date']:%Y-%m-%d} ลูกค้า {d['customer']} P-line {d['pline']}: ไม่มีค่า Margin")
            continue
        t = find_tier(m, tiers)
        d["tier"] = t["name"] if t else BELOW
        d["rate"] = t["rates"][d["category"]] if t else 0.0
        d["incentive"] = round(d["amount"] * d["rate"], 2) + 0.0  # +0.0 กัน -0.0
    if problems:
        raise SystemExit(f"❌ มี {len(problems)} แถวที่หาอัตราไม่ได้ (ตัวอย่าง):\n  " + "\n  ".join(problems[:10]))

    out = Path(a.outdir)
    clear_output(out)

    # File 2: raw data ของปีที่คำนวณ + Type / Margin Tier / Commission %
    # ไม่แสดงตัวเลข Margin จริง (ตัดคอลัมน์ margin ออก) — Sale เห็นแค่ Tier
    hidden = {margin_col, *(cfg.get("hide_columns") or [])}
    out_header = [h for h in header if h not in hidden]
    extra = ["Type", "Margin Tier", "Calculated Commission %", "Commission (THB)"]
    with open(out / f"raw_data_{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header + extra, extrasaction="ignore")
        w.writeheader()
        for d in detail:
            w.writerow({**d["raw"], "Type": d["category"], "Margin Tier": d["tier"],
                        "Calculated Commission %": f"{d['rate']:.2%}", "Commission (THB)": d["incentive"]})

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
