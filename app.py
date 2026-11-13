"""หน้าเว็บคำนวณ Sales Commission (หลายบริษัท)

รัน:  streamlit run app.py
ตั้งรหัสผ่าน (แนะนำ): ตั้ง environment variable APP_PASSWORD ก่อนรัน
"""
import hashlib
import io
import math
import os
import tempfile
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

import companies
import incentive as core
import theme

APP_DIR = Path(__file__).resolve().parent
st.set_page_config(page_title="Sales Commission | Chaiyaboon", page_icon="🔴", layout="wide",
                   initial_sidebar_state="expanded")
theme.apply()

# รูปแบบตัวเลขในตาราง: "localized" (มีคอมม่า) ใช้ได้ตั้งแต่ Streamlit 1.43 — รุ่นเก่า (เช่น 1.40 บน Python 3.8) ใช้ printf
try:
    _ST_VER = tuple(int(x) for x in st.__version__.split(".")[:2])
except ValueError:
    _ST_VER = (0, 0)
MONEY_FMT = "localized" if _ST_VER >= (1, 43) else "%.2f"

def money_table(rows, money_cols, pct_cols=()):
    """ตารางแสดงผล: ตัวเลขมีคอมม่าคั่นหลักพัน (ใช้ pandas Styler — รองรับ Streamlit ทุกรุ่น และยังเรียงตามตัวเลขได้)"""
    df = pd.DataFrame(rows)
    fmt = {c: "{:,.2f}" for c in money_cols if c in df.columns}
    fmt.update({c: "{:.3f}" for c in pct_cols if c in df.columns})
    return df.style.format(fmt, na_rep="")


# คอลัมน์ของตารางที่อาจว่างตั้งแต่แรก
EMPTY_COLUMNS = {
    "new_product": ["Item No.", "Commission (%)"],
    "fsa": ["Saleman", "P-line", "เดือน (1-12)", "FSA (บาท)"],
    "machine_std": ["ยอดขาย/เดือน ตั้งแต่ (บาท)", "Commission (%)"],
    "machine_proj": ["ยอดขาย/เดือน ตั้งแต่ (บาท)", "Commission (%)"],
}
# Tier ที่ไม่ได้ Commission (แสดงจุดสีเทา)
ZERO_TIERS = {"BELOW LOW", "NO COMMISSION", "NOT ELIGIBLE", "NO SALEMAN", "UNPAID", "NO FSA", "BELOW FSA",
              "BELOW TIER", "BELOW MIN PRICE", "UNMAPPED"}
RULE_HELP = {
    "CBG": "<b>ลำดับการคิด</b><br>1. USDB / ต้นทุน 0 → NO COMMISSION<br>2. Margin ต่ำกว่า LOW → BELOW LOW<br>"
           "3. Item ใน New Product → NEW PRODUCT<br>4. อื่น ๆ → Type × LOW / MID / HIGH",
    "SAS": "<b>กฎ</b><br>วัสดุ (P-class ≠ GTP) · เครื่องจักร GTP · เครื่องจักร GTP ขายให้ BU BDI",
    "CM": "<b>กฎ</b><br>วัสดุ: ยอด Saleman × P-line × เดือน ต้องถึง % ของ FSA<br>"
          "เครื่องจักร: ขั้นบันไดตามยอดต่อเดือน ใช้ % กับยอดทั้งก้อน<br>ต่ำกว่า MIN Price ต้องมี MD อนุมัติ",
    "DAP UV": "<b>กฎ</b><br>Flat rate ทุกสินค้า",
}
RULE_HELP["SC"] = RULE_HELP["CBG"]  # Silkcut ใช้กฎเดียวกับ CBG


def check_password():
    pw = os.environ.get("APP_PASSWORD")
    if not pw or st.session_state.get("authed"):
        return True
    st.markdown("<style>section[data-testid='stSidebar'],[data-testid='collapsedControl']{display:none}</style>",
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.write("")
        st.write("")
        with st.container(border=False, key="card_login"):
            theme.login_head("Sales Commission", "ระบบคำนวณค่าคอมมิชชั่นพนักงานขาย")
            with st.form("login", border=False):
                entered = st.text_input("รหัสผ่าน", type="password", placeholder="ใส่รหัสผ่าน")
                ok = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            if ok:
                if entered == pw:
                    st.session_state["authed"] = True
                    st.rerun()
                st.error("รหัสผ่านไม่ถูกต้อง")
        theme.footer()
    return False


def clean(records):
    """DataFrame records -> list ของ dict (NaN -> None, ตัด whitespace)"""
    out = []
    for r in records:
        row = {}
        for k, v in r.items():
            if isinstance(v, float) and math.isnan(v):
                v = None
            elif isinstance(v, str):
                v = v.strip() or None
            row[k] = v
        if any(v is not None for v in row.values()):
            out.append(row)
    return out


@st.cache_data(show_spinner=False, max_entries=4)
def salesmen_in_file(data: bytes, name: str, delimiter: str, sales_col: str, name_col: str):
    """รหัส Saleman ในไฟล์ + ชื่อ (จากคอลัมน์ชื่อใน report ถ้ามี) -> (ids, {id: ชื่อ}, ชื่อคอลัมน์ที่ใช้)"""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / name
        p.write_bytes(data)
        header, rows = core.read_table(p, delimiter)
    if sales_col not in header:
        return [], {}, None
    ncol = companies.find_name_column(header, name_col)
    names = {}
    if ncol:
        seen = {}
        for r in rows:
            sid, nm = core.cell_str(r.get(sales_col)), core.cell_str(r.get(ncol))
            if sid and nm:
                seen.setdefault(sid, Counter())[nm] += 1
        names = {sid: c.most_common(1)[0][0] for sid, c in seen.items()}
    return sorted({core.cell_str(r.get(sales_col)) for r in rows} - {""}), names, ncol


def tier_label(t):
    return f"{'○' if t in ZERO_TIERS else '●'} {t}"


if not check_password():
    st.stop()

cfg = core.load_config(APP_DIR / "config.yaml")

# ---------------------------------------------------------------- sidebar
theme.sidebar_logo()
theme.side_label("บริษัท")
theme.company_nav_css(list(companies.COMPANIES))
code = st.sidebar.radio("บริษัท", list(companies.COMPANIES), label_visibility="collapsed",
                        format_func=lambda c: companies.COMPANY_NAMES.get(c, c))
theme.side_label("วิธีคิด")
theme.side_help(RULE_HELP.get(code, ""))

# ---------------------------------------------------------------- page head
head_l, head_r = st.columns([3, 2], vertical_alignment="bottom")
with head_l:
    theme.page_head(["Sales Commission", code], f"{companies.COMPANY_NAMES.get(code, code)}",
                    [f"{code} Commission", companies.COMPANIES[code]], code=code)
specs = companies.table_specs(code)
if not specs:
    st.info(f"{code}: ยังไม่มีข้อกำหนดการคำนวณ")
    theme.footer()
    st.stop()
with head_r:
    a1, a2 = st.columns(2)
    save_clicked = a1.button("บันทึกเป็นค่า default", use_container_width=True,
                             help="ใช้ค่าในตารางนี้เป็นค่าเริ่มต้นครั้งต่อไป")
    reset_clicked = a2.button("คืนค่าเริ่มต้น", use_container_width=True,
                              help="ล้างค่าที่บันทึกไว้ กลับไปใช้ค่าเริ่มต้นของระบบ")

skey = f"settings_{code}"
if reset_clicked:
    companies.reset_settings(code)
    st.session_state.pop(skey, None)
    for k in [k for k in st.session_state if k.startswith(f"ed_{code}_")]:
        st.session_state.pop(k)
    st.rerun()
if skey not in st.session_state:
    st.session_state[skey] = companies.load_settings(code)
saleman_names = {}  # ชื่อ Saleman มาจาก report (คอลัมน์ columns.salesperson_name ใน config.yaml)
tables, saved_eligible = st.session_state[skey]

# ---------------------------------------------------------------- อัตรา
edited = {}
with st.container(border=False, key="card_rates"):
    theme.card_head("อัตรา Commission", "แก้ค่าในตารางได้เลย — ใช้กับการคำนวณรอบนี้ · ค่า % กรอกเป็นตัวเลข เช่น 0.5 = 0.5%")
    tabs = st.tabs([t[1] for t in specs])
    for tab, (key, title, help_text, fixed, locked) in zip(tabs, specs):
        with tab:
            st.caption(help_text)
            rows = tables.get(key) or []
            df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EMPTY_COLUMNS.get(key, []))
            colcfg = {}
            for c in df.columns:
                if "(%)" in c or "% ของ" in c:
                    colcfg[c] = st.column_config.NumberColumn(c, format="%.3f", min_value=0.0)
                elif "(บาท)" in c:
                    colcfg[c] = st.column_config.NumberColumn(c, format=MONEY_FMT, min_value=0.0)
                elif c == "เดือน (1-12)":
                    colcfg[c] = st.column_config.NumberColumn(c, min_value=1, max_value=12, step=1)
                else:
                    colcfg[c] = st.column_config.TextColumn(c)
            res_df = st.data_editor(df, key=f"ed_{code}_{key}", hide_index=True, use_container_width=True,
                                    num_rows="fixed" if fixed else "dynamic", disabled=locked, column_config=colcfg)
            edited[key] = clean(res_df.to_dict("records"))

# ---------------------------------------------------------------- ไฟล์ยอดขาย
eligible_rows = []
with st.container(border=False, key="card_upload"):
    theme.card_head("ไฟล์ยอดขาย", "ไฟล์จากระบบ (.txt / .csv / .xlsx) — ระบบซ่อนต้นทุนและ Margin ในไฟล์ผลลัพธ์")
    up_col, opt_col = st.columns([3, 1.2])
    with up_col:
        sales_file = st.file_uploader("ไฟล์ยอดขาย", type=["txt", "csv", "xlsx"], label_visibility="collapsed")
    with opt_col:
        st.caption("คำนวณปีล่าสุดในไฟล์ · ใช้ข้อมูลปีก่อนหน้าเป็นประวัติอ้างอิง")
        run = st.button("คำนวณ Commission", type="primary", disabled=sales_file is None, use_container_width=True)
    if sales_file is not None:
        found, saleman_names, name_col = salesmen_in_file(
            sales_file.getvalue(), Path(sales_file.name).name, cfg.get("delimiter"),
            cfg["columns"]["salesperson"], cfg["columns"].get("salesperson_name", "Saleman Name"))
        n_off = sum(1 for s in found if not saved_eligible.get(s, True))
        with st.expander(f"Saleman ที่มีสิทธิ์รับ Commission · {len(found) - n_off}/{len(found)} คน"):
            st.caption("เอาเครื่องหมายออกสำหรับคนที่ไม่มีสิทธิ์ · จำค่าไว้เมื่อกด 'บันทึกเป็นค่า default'"
                       + ("" if name_col else " · ยังไม่มีคอลัมน์ชื่อ Saleman ในไฟล์ — แสดงเฉพาะรหัส"))
            el_df = pd.DataFrame([{"Saleman": s, "ชื่อ": saleman_names.get(s, ""),
                                   "มีสิทธิ์": bool(saved_eligible.get(s, True))} for s in found])
            el_df = st.data_editor(el_df, key=f"el_{code}_{hashlib.md5(sales_file.getvalue()[:4096]).hexdigest()}",
                                   hide_index=True, use_container_width=True, num_rows="fixed",
                                   disabled=["Saleman", "ชื่อ"],
                                   column_config={"ชื่อ": st.column_config.TextColumn("ชื่อ (จาก report)", width="large"),
                                                  "มีสิทธิ์": st.column_config.CheckboxColumn("มีสิทธิ์", width="small")})
            eligible_rows = el_df.to_dict("records")

if save_clicked:
    elig_map = dict(saved_eligible)
    elig_map.update({r["Saleman"]: bool(r["มีสิทธิ์"]) for r in eligible_rows})
    companies.save_settings(code, edited, elig_map)
    st.session_state[skey] = companies.load_settings(code)
    st.toast(f"บันทึกค่า default ของ {code} แล้ว", icon="✅")

# ---------------------------------------------------------------- คำนวณ
if run:
    eligible = {r["Saleman"] for r in eligible_rows if r["มีสิทธิ์"]} if eligible_rows else None
    with tempfile.TemporaryDirectory() as tmp, st.spinner("กำลังคำนวณ..."):
        sp = Path(tmp) / Path(sales_file.name).name
        sp.write_bytes(sales_file.getvalue())
        try:
            res = companies.compute(code, sp, cfg, edited, None, eligible)  # ปีล่าสุดในไฟล์เสมอ
            companies.attach_saleman_names(res, saleman_names, cfg["columns"]["salesperson"])
            buf = io.BytesIO()
            core.save_excel(res, buf)
        except SystemExit as e:
            st.error(str(e))
            st.stop()
        except Exception as e:  # ไฟล์ผิดรูปแบบ ฯลฯ
            st.error(f"คำนวณไม่สำเร็จ: {e}")
            st.stop()
    st.session_state["result"] = (code, res, buf.getvalue())

# ---------------------------------------------------------------- ผลลัพธ์
if st.session_state.get("result") and st.session_state["result"][0] == code:
    _, res, xlsx = st.session_state["result"]
    y = res["year"]
    detail = res["detail"]
    total = sum(res["col_total"])
    earned = sum(1 for d in detail if d["incentive"] != 0)

    st.write("")
    theme.kpis([
        (f"Commission รวม ปี {y}", f"฿{total:,.2f}", True),
        ("Saleman", f"{len(res['names']):,}", False),
        ("แถวที่คำนวณ", f"{len(detail):,}", False),
        ("แถวที่ได้ Commission", f"{earned:,} ({earned / max(len(detail), 1):.0%})", False),
    ])
    for w in res["warnings"]:
        st.warning(w, icon="⚠️")

    with st.container(border=False, key="card_result"):
        h1, h2 = st.columns([3, 1.3], vertical_alignment="center")
        with h1:
            theme.card_head("ผลการคำนวณ", f"ปี {y} · ตามเดือน Invoice")
        with h2:
            fname = f"incentive_{code.replace(' ', '_')}_{y}.xlsx"
            st.download_button("ดาวน์โหลด Excel", xlsx, fname, type="primary", use_container_width=True,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        t1, t2, t3 = st.tabs(["Sale Summary", "Commission Tier", "รายการ"])
        with t1:
            nm = res.get("saleman_names") or saleman_names
            table = [{"Saleman": n, "ชื่อ": nm.get(n, ""),
                      **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["monthly"][n])},
                      "Total": round(sum(res["monthly"][n]), 2)} for n in res["names"]]
            table.append({"Saleman": "Total", "ชื่อ": "",
                          **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["col_total"])},
                          "Total": round(total, 2)})
            st.dataframe(money_table(table, core.MONTH_NAMES + ["Total"]), hide_index=True, use_container_width=True,
                         column_config={"ชื่อ": st.column_config.TextColumn("ชื่อ", width="medium")})
        cnt, amt = Counter(), Counter()
        for d in detail:
            cnt[d["tier"]] += 1
            amt[d["tier"]] += d["incentive"]
        with t2:
            st.dataframe(money_table([{"Commission Tier": tier_label(k), "แถว": f"{v:,}", "Commission (THB)": round(amt[k], 2)}
                                      for k, v in cnt.most_common()], ["Commission (THB)"]),
                         hide_index=True, use_container_width=True)
        with t3:
            opts = ["ทั้งหมด"] + [k for k, _ in cnt.most_common()]
            pick = st.radio("กรอง", opts, horizontal=True, label_visibility="collapsed",
                            format_func=lambda o: f"{o} · {len(detail) if o == 'ทั้งหมด' else cnt[o]:,}")
            rows = [d for d in detail if pick == "ทั้งหมด" or d["tier"] == pick]
            raw = lambda d, c: core.cell_str(d["raw"].get(c))
            nm = res.get("saleman_names") or saleman_names
            st.dataframe(money_table([{
                "วันที่": d["date"].strftime("%Y-%m-%d"), "Invoice": raw(d, "Invoice No."),
                "Saleman": d["salesperson"], "ชื่อ Saleman": nm.get(d["salesperson"], ""),
                "ลูกค้า": raw(d, "Customer Name") or d["customer"],
                "P-line": d["pline"], "ยอดขาย": round(d["amount"], 2),
                "ประเภท": d["out"].get("Type") or d["out"].get("Product Group"),
                "Tier": tier_label(d["tier"]), "%": round(d["rate"] * 100, 3), "Commission": d["incentive"],
            } for d in rows[:1000]], ["ยอดขาย", "Commission"], ["%"]),
                hide_index=True, use_container_width=True, height=420,
                column_config={"ชื่อ Saleman": st.column_config.TextColumn("ชื่อ Saleman", width="medium")})
            if len(rows) > 1000:
                st.caption(f"แสดง 1,000 จาก {len(rows):,} แถว — ดูทั้งหมดในไฟล์ Excel")

theme.footer()
