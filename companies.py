"""กฎ Commission ของแต่ละบริษัท + ตารางค่า default + การบันทึกค่า

ค่า % ในตารางทั้งหมดเก็บเป็นหน่วย % (เช่น 0.4 = 0.4%) แล้วแปลงเป็นสัดส่วนตอนคำนวณ
ค่าที่ผู้ใช้กด "บันทึกเป็นค่า default" เก็บที่ data/company_settings/<บริษัท>.json (ไม่ขึ้น git)
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import incentive as core

SETTINGS_DIR = Path(__file__).resolve().parent / "data" / "company_settings"

# ---------------------------------------------------------------- ตาราง default
def _cbg_defaults():
    """CBG: ใช้ค่าจาก data/rates.xlsx เดิมถ้ามี ไม่งั้นใช้ MIN ตามเอกสาร (40/60/80) และอัตรา 0"""
    rates_xlsx = Path(__file__).resolve().parent / "data" / "rates.xlsx"
    tiers, newp = None, {}
    if rates_xlsx.exists():
        try:
            tiers = core.load_rates(rates_xlsx)
            newp = core.load_new_products(rates_xlsx)
        except SystemExit:
            tiers = None
    if not tiers:
        tiers = [{"name": n, "min": m, "rates": {t: 0.0 for t in core.CATEGORIES}}
                 for n, m in (("LOW", 0.4), ("MID", 0.6), ("HIGH", 0.8))]
    names = [t["name"] for t in tiers]
    return {
        "type_tier": [{"Type": ty, **{f"{t['name']} (%)": round(t["rates"][ty] * 100, 4) for t in tiers}}
                      for ty in core.CATEGORIES],
        "tier_min": [{"Tier": t["name"], "MIN Margin (%)": round(t["min"] * 100, 4)} for t in tiers],
        "new_product": [{"Item No.": k, "Commission (%)": round(v * 100, 4)} for k, v in newp.items()],
        "_tier_names": names,
    }


def _defaults(code):
    if code == "CBG":
        d = _cbg_defaults()
        d.pop("_tier_names")
        return d
    if code == "SAS":
        return {"rates": [
            {"กลุ่ม": "MATERIAL", "เงื่อนไข": "Product Class ≠ GTP (ทุก BU)", "Commission (%)": 0.01},
            {"กลุ่ม": "MACHINE", "เงื่อนไข": "Product Class = GTP, BU ≠ BDI", "Commission (%)": 1.0},
            {"กลุ่ม": "MACHINE (BDI)", "เงื่อนไข": "Product Class = GTP, BU = BDI", "Commission (%)": 0.8},
        ]}
    if code == "CM":
        return {
            "material": [{"Commission (%)": 0.40, "ต้องถึง % ของ FSA": 70.0}],
            "machine_std": [{"ยอดขาย/เดือน ตั้งแต่ (บาท)": v, "Commission (%)": r} for v, r in
                            ((50000, 0.25), (200001, 0.375), (300001, 0.5), (400001, 0.625), (600001, 0.75))],
            "machine_proj": [{"ยอดขาย/เดือน ตั้งแต่ (บาท)": v, "Commission (%)": r} for v, r in
                             ((100000, 0.25), (300000, 0.5), (500000, 1.0))],
            "fsa": [],
        }
    if code == "DAP UV":
        return {"rates": [{"กลุ่ม": "ALL", "Commission (%)": 0.5}]}
    return {}


# ---------------------------------------------------------------- นิยามตารางสำหรับหน้าเว็บ
def table_specs(code):
    """คืน list ของ (key, ชื่อตาราง, คำอธิบาย, rows คงที่?, คอลัมน์ที่แก้ไม่ได้)"""
    if code == "CBG":
        return [
            ("type_tier", "Commission % ตาม Type × Tier", "OCOP / OCNP / NC × LOW / MID / HIGH", True, ["Type"]),
            ("tier_min", "MIN Margin ของแต่ละ Tier", "Margin ≥ MIN ของ Tier ไหน ได้ Tier สูงสุดนั้น; ต่ำกว่า LOW = BELOW LOW",
             True, ["Tier"]),
            ("new_product", "New Product (Flat rate ต่อ Item)", "Item ที่อยู่ในตารางนี้ได้ % ตามตาราง (ยังต้องผ่าน MIN ของ LOW)",
             False, []),
        ]
    if code == "SAS":
        return [("rates", "Commission %", "วัสดุ / เครื่องจักร (GTP) / เครื่องจักรขายให้ BDI", True, ["กลุ่ม", "เงื่อนไข"])]
    if code == "CM":
        return [
            ("material", "วัสดุ / สิ้นเปลือง (P-line ที่ไม่ขึ้นต้นด้วย 5)",
             "ได้ % นี้เมื่อยอดขายของ Saleman × P-line × เดือน ถึง % ของ FSA ที่กำหนด", True, []),
            ("fsa", "เป้าขาย FSA (บาท)", "หนึ่งแถว = Saleman × P-line × เดือน — วางจาก Excel ได้", False, []),
            ("machine_std", "เครื่องจักร Standard (P-line 5XXXX01)",
             "ขั้นบันไดตามยอดขายเครื่องจักร Standard ต่อ Saleman ต่อเดือน; % ของขั้นที่ถึงใช้กับยอดทั้งก้อน", False, []),
            ("machine_proj", "เครื่องจักร Project (P-line 5XXXX02)",
             "ขั้นบันไดตามยอดขายเครื่องจักร Project ต่อ Saleman ต่อเดือน; % ของขั้นที่ถึงใช้กับยอดทั้งก้อน", False, []),
        ]
    if code == "DAP UV":
        return [("rates", "Commission %", "Flat rate ทุกสินค้า", True, ["กลุ่ม"])]
    return []


COMPANIES = {
    "CBG": "Type (NC/OCNP/OCOP) × Margin Tier + New Product",
    "SAS": "Flat rate: วัสดุ / เครื่องจักร / เครื่องจักร BDI",
    "CM": "วัสดุ (ต้องถึง FSA) + เครื่องจักรขั้นบันไดรายเดือน",
    "DAP UV": "Flat rate",
    "SC": "ยังไม่มีข้อกำหนด",
}


def load_settings(code):
    """ค่าที่บันทึกไว้ (ถ้ามี) ไม่งั้นใช้ default; คืน (tables, eligible dict)"""
    tables, eligible = _defaults(code), {}
    f = SETTINGS_DIR / f"{code.replace(' ', '_')}.json"
    if f.exists():
        saved = json.loads(f.read_text(encoding="utf-8"))
        tables.update({k: v for k, v in saved.get("tables", {}).items() if k in tables})
        eligible = saved.get("eligible", {})
    return tables, eligible


def save_settings(code, tables, eligible):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    f = SETTINGS_DIR / f"{code.replace(' ', '_')}.json"
    f.write_text(json.dumps({"tables": tables, "eligible": eligible, "saved_at": datetime.now().isoformat()},
                            ensure_ascii=False, indent=2), encoding="utf-8")


def reset_settings(code):
    f = SETTINGS_DIR / f"{code.replace(' ', '_')}.json"
    if f.exists():
        f.unlink()


# ---------------------------------------------------------------- helpers
def _num(v, what):
    if v is None or (isinstance(v, float) and v != v) or str(v).strip() == "":
        raise SystemExit(f"❌ ยังไม่ได้กรอก: {what}")
    try:
        return float(str(v).replace(",", "").rstrip("%"))
    except ValueError:
        raise SystemExit(f"❌ ค่าไม่ใช่ตัวเลข: {what} = {v}")


def _pct(v, what):
    return _num(v, what) / 100


def _tiers(rows, label):
    out = []
    for i, r in enumerate(rows, 1):
        lo = r.get("ยอดขาย/เดือน ตั้งแต่ (บาท)")
        rate = r.get("Commission (%)")
        if (lo is None or str(lo).strip() == "") and (rate is None or str(rate).strip() == ""):
            continue
        out.append((_num(lo, f"{label} แถว {i} ยอดขาย"), _pct(rate, f"{label} แถว {i} Commission %")))
    out.sort()
    if len({lo for lo, _ in out}) != len(out):
        raise SystemExit(f"❌ {label}: มียอดขั้นต่ำซ้ำกัน")
    return out


def _tier_rate(total, tiers):
    hit = None
    for i, (lo, rate) in enumerate(tiers, 1):
        if total >= lo:
            hit = (i, rate)
    return hit


def _add_months(dt, n):
    m = dt.month - 1 + n
    return f"{dt.year + m // 12}-{m % 12 + 1:02d}"


# ---------------------------------------------------------------- คำนวณ
def compute(code, sales_path, cfg, tables, year=None, eligible=None):
    """คำนวณ Commission ตามกฎของบริษัท คืน dict ผลลัพธ์ (รูปแบบเดียวกับ incentive.compute_cbg)"""
    if code == "CBG":
        tiers, newp = cbg_from_tables(tables)
        res = core.compute_cbg(sales_path, cfg, year, tiers, newp, eligible)
    elif code in ("SAS", "CM", "DAP UV"):
        res = _compute_generic(code, sales_path, cfg, tables, year, eligible)
    else:
        raise SystemExit(f"❌ ยังไม่มีกฎการคำนวณของ {code}")
    res["settings"] = [(table_specs(code)[i][1], tables[k]) for i, (k, *_r) in enumerate(table_specs(code))]
    if eligible is not None:
        res["settings"].append(("Saleman ที่มีสิทธิ์รับ Commission",
                                [{"Saleman": s, "มีสิทธิ์": "✓"} for s in sorted(eligible)]))
    return res


def cbg_from_tables(tables):
    tiers = []
    mins = {str(r["Tier"]).upper(): r.get("MIN Margin (%)") for r in tables["tier_min"]}
    for name, mn in mins.items():
        rates = {}
        for r in tables["type_tier"]:
            ty = str(r["Type"]).upper()
            rates[ty] = _pct(r.get(f"{name} (%)"), f"{ty} / {name}")
        tiers.append({"name": name, "min": _pct(mn, f"MIN ของ {name}"), "rates": rates})
    if len({t["min"] for t in tiers}) != len(tiers):
        raise SystemExit("❌ MIN Margin ของแต่ละ Tier ต้องไม่ซ้ำกัน")
    newp = {}
    for i, r in enumerate(tables.get("new_product") or [], 1):
        item = str(r.get("Item No.") or "").strip()
        rate = r.get("Commission (%)")
        if not item and (rate is None or str(rate).strip() == "" or rate != rate):
            continue
        if not item:
            raise SystemExit(f"❌ New Product แถว {i}: มี % แต่ไม่มี Item No.")
        if item.upper() in newp:
            raise SystemExit(f"❌ New Product: Item {item} ซ้ำ")
        newp[item.upper()] = _pct(rate, f"New Product {item}")
    return tiers, newp


def _compute_generic(code, sales_path, cfg, tables, year, eligible):
    cols = cfg["columns"]
    warnings = []
    rows, header = core.load_sales(sales_path, cols, cfg.get("delimiter"))
    if not rows:
        raise SystemExit("❌ ไม่มียอดขายในไฟล์")
    year = year or max(r["date"].year for r in rows)
    rows = [r for r in rows if r["date"].year == year]
    if not rows:
        raise SystemExit(f"❌ ไม่มียอดขายของปี {year} ในไฟล์")

    def col(key, default):
        name = cols.get(key, default)
        return name if name in header else None

    pclass_col, bu_col = col("product_class", "P-class"), col("bu", "BU")
    qty_col, minp_col = col("qty", "Qty"), col("min_price", "MIN Price")
    pay = cfg.get("payment") or {}
    paid_col = pay.get("paid_date_column")
    paid_col = paid_col if paid_col in header else None
    if not paid_col:
        warnings.append("ยังไม่มีคอลัมน์วันที่รับชำระในไฟล์ — คิดจากยอด Invoice ทั้งหมด "
                        "(เครื่องจักรแสดงรอบจ่ายเป็น 'รอข้อมูลชำระ')")
    approve_col = pay.get("md_approval_column")
    approve_col = approve_col if approve_col in header else None

    def raw(d, c):
        return core.cell_str(d["raw"].get(c)) if c else ""

    # ---- จัดกลุ่มสินค้า + ข้อกำหนดร่วม ----
    for d in rows:
        d["group"] = _group(code, d, raw(d, pclass_col), raw(d, bu_col))
        d["paid_date"] = None
        if paid_col and raw(d, paid_col):
            try:
                d["paid_date"] = core.parse_date(raw(d, paid_col)[:10])
            except ValueError:
                pass

    def finish(d, tier, rate):
        d["tier"], d["rate"] = tier, rate
        d["incentive"] = round(d["amount"] * rate, 2) + 0.0

    active = []
    for d in rows:
        if not d["salesperson"]:
            finish(d, core.NO_SALEMAN, 0.0)
        elif eligible is not None and d["salesperson"] not in eligible:
            finish(d, core.NOT_ELIGIBLE, 0.0)
        elif paid_col and d["paid_date"] is None:
            finish(d, "UNPAID", 0.0)
        else:
            active.append(d)

    # ---- กฎของแต่ละบริษัท ----
    if code == "SAS":
        rates = {str(r["กลุ่ม"]).upper(): _pct(r.get("Commission (%)"), f"SAS {r['กลุ่ม']}") for r in tables["rates"]}
        if not pclass_col:
            raise SystemExit("❌ ไม่พบคอลัมน์ Product Class (P-class) ในไฟล์")
        for d in active:
            finish(d, d["group"], rates[d["group"]])

    elif code == "DAP UV":
        rate = _pct(tables["rates"][0].get("Commission (%)"), "DAP UV Commission %")
        for d in active:
            finish(d, "FLAT", rate)

    elif code == "CM":
        m = tables["material"][0]
        mat_rate = _pct(m.get("Commission (%)"), "CM วัสดุ Commission %")
        fsa_pct = _pct(m.get("ต้องถึง % ของ FSA"), "CM % ของ FSA")
        std = _tiers(tables["machine_std"], "เครื่องจักร Standard")
        proj = _tiers(tables["machine_proj"], "เครื่องจักร Project")
        fsa = {}
        for i, r in enumerate(tables.get("fsa") or [], 1):
            s, pl, mo, tg = (str(r.get("Saleman") or "").strip(), str(r.get("P-line") or "").strip(),
                             r.get("เดือน (1-12)"), r.get("FSA (บาท)"))
            if not s and not pl and (tg is None or str(tg).strip() == "" or tg != tg):
                continue
            mo = int(_num(mo, f"FSA แถว {i} เดือน"))
            fsa[(s, pl.upper(), mo)] = _num(tg, f"FSA แถว {i} เป้า")

        # เครื่องจักรที่ขายต่ำกว่า MIN Price และ MD ยังไม่อนุมัติ: ไม่ได้ Commission และไม่นับรวมยอดขั้นบันได
        def below_min_price(d):
            q = raw(d, qty_col)
            try:
                unit = d["amount"] / float(q) if q and float(q) != 0 else d["amount"]
                mp = float(raw(d, minp_col) or 0) if minp_col else 0
            except ValueError:
                return False
            return mp > 0 and unit < mp and not raw(d, approve_col)

        for d in list(active):
            if d["group"] in ("MACHINE STD", "MACHINE PROJECT") and below_min_price(d):
                finish(d, "BELOW MIN PRICE", 0.0)
                active.remove(d)

        # ยอดรวมต่อเดือน (ใช้เฉพาะแถวที่นับได้)
        mat_sum, mach_sum = defaultdict(float), defaultdict(float)
        for d in active:
            mo = d["date"].month
            if d["group"] == "MATERIAL":
                mat_sum[(d["salesperson"], d["pline"].upper(), mo)] += d["amount"]
            elif d["group"] in ("MACHINE STD", "MACHINE PROJECT"):
                mach_sum[(d["salesperson"], d["group"], mo)] += d["amount"]
        no_fsa = set()
        for d in active:
            mo, g = d["date"].month, d["group"]
            if g == "MATERIAL":
                key = (d["salesperson"], d["pline"].upper(), mo)
                target = fsa.get(key)
                if target is None:
                    no_fsa.add(key)
                    finish(d, "NO FSA", 0.0)
                elif mat_sum[key] >= fsa_pct * target:
                    finish(d, "MATERIAL", mat_rate)
                else:
                    finish(d, "BELOW FSA", 0.0)
            elif g in ("MACHINE STD", "MACHINE PROJECT"):
                hit = _tier_rate(mach_sum[(d["salesperson"], g, mo)], std if g == "MACHINE STD" else proj)
                if hit:
                    finish(d, f"{'STD' if g == 'MACHINE STD' else 'PROJECT'} T{hit[0]}", hit[1])
                else:
                    finish(d, "BELOW TIER", 0.0)
            else:
                finish(d, "UNMAPPED", 0.0)
        if no_fsa:
            warnings.append(f"ไม่มีเป้า FSA {len(no_fsa)} รายการ (Saleman × P-line × เดือน) — วัสดุในรายการเหล่านี้ได้ 0 (NO FSA)")
        if not approve_col and any(d.get("tier") == "BELOW MIN PRICE" for d in rows):
            warnings.append("ไม่พบคอลัมน์การอนุมัติของ MD — เครื่องจักรที่ขายต่ำกว่า MIN Price ได้ 0 ทั้งหมด")
        unm = sum(1 for d in active if d["tier"] == "UNMAPPED")
        if unm:
            warnings.append(f"มี {unm} แถวที่ P-line ขึ้นต้นด้วย 5 แต่ไม่ลงท้าย 01/02 — ได้ 0 (UNMAPPED)")

    # ---- รอบจ่าย ----
    for d in rows:
        if d["tier"] == "UNPAID":
            d["payout"] = "รอชำระ"
        elif d["rate"] == 0:
            d["payout"] = "-"
        elif d["group"].startswith("MACHINE"):
            if d["paid_date"]:
                pd = d["paid_date"]
                d["payout"] = _add_months(pd, 0 if pd.day < 20 else 1)
            else:
                d["payout"] = "รอข้อมูลชำระ"
        else:
            d["payout"] = _add_months(d["date"], 4)
        d["out"] = {"Product Group": d["group"], "Commission Tier": d["tier"], "Payout Month": d["payout"]}

    w = core.no_saleman_warning(rows)
    if w:
        warnings.append(w)
    return _result(rows, header, cfg, year, warnings, title=f"{code} — Commission ปี {year} (ตามเดือน Invoice)")


def _group(code, d, pclass, bu):
    pl = d["pline"].upper()
    if code == "SAS":
        if pclass.upper() == "GTP":
            return "MACHINE (BDI)" if bu.upper() == "BDI" else "MACHINE"
        return "MATERIAL"
    if code == "CM":
        if not pl.startswith("5"):
            return "MATERIAL"
        if pl.endswith("01"):
            return "MACHINE STD"
        if pl.endswith("02"):
            return "MACHINE PROJECT"
        return "MACHINE ?"
    return "ALL"


def _result(detail, header, cfg, year, warnings, title):
    margin_col = cfg["columns"].get("margin")
    hidden = {margin_col, *(cfg.get("hide_columns") or [])}
    out_header = [h for h in header if h not in hidden]
    date_col = cfg["columns"].get("date")
    add_my = [c for c in ("Month", "Year") if c not in header]
    if date_col in out_header and add_my:
        i = out_header.index(date_col) + 1
        out_header[i:i] = add_my
    extra = ["Product Group", "Commission Tier", "Calculated Commission %", "Commission (THB)", "Payout Month"]
    monthly = defaultdict(lambda: [0.0] * 12)
    for d in detail:
        if d["salesperson"]:
            monthly[d["salesperson"]][d["date"].month - 1] += d["incentive"]
    names = sorted(monthly)
    col_total = [sum(monthly[n][m] for n in names) for m in range(12)]
    return {"year": year, "lookback": 0, "warnings": warnings, "names": names, "title": title,
            "monthly": dict(monthly), "col_total": col_total, "raw_cols": out_header + extra,
            "detail": detail, "date_col": date_col}
