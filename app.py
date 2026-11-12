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

APP_DIR = Path(__file__).resolve().parent
st.set_page_config(page_title="Sales Commission", page_icon="💰", layout="wide")

# คอลัมน์ของตารางที่อาจว่างตั้งแต่แรก
EMPTY_COLUMNS = {
    "new_product": ["Item No.", "Commission (%)"],
    "fsa": ["Saleman", "P-line", "เดือน (1-12)", "FSA (บาท)"],
    "machine_std": ["ยอดขาย/เดือน ตั้งแต่ (บาท)", "Commission (%)"],
    "machine_proj": ["ยอดขาย/เดือน ตั้งแต่ (บาท)", "Commission (%)"],
}


def check_password():
    pw = os.environ.get("APP_PASSWORD")
    if not pw or st.session_state.get("authed"):
        return True
    st.title("💰 Sales Commission")
    entered = st.text_input("รหัสผ่าน", type="password")
    if entered:
        if entered == pw:
            st.session_state["authed"] = True
            st.rerun()
        st.error("รหัสผ่านไม่ถูกต้อง")
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
def salesmen_in_file(data: bytes, name: str, delimiter: str, sales_col: str):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / name
        p.write_bytes(data)
        header, rows = core.read_table(p, delimiter)
    if sales_col not in header:
        return []
    return sorted({core.cell_str(r.get(sales_col)) for r in rows} - {""})


if not check_password():
    st.stop()

cfg = core.load_config(APP_DIR / "config.yaml")

st.title("💰 Sales Commission")
st.caption("① เลือกบริษัท → ② ตรวจ/แก้อัตรา → ③ อัปโหลดไฟล์ยอดขาย → ④ คำนวณและดาวน์โหลด Excel")

# ---------------------------------------------------------------- ① บริษัท
code = st.selectbox("① บริษัท", list(companies.COMPANIES), format_func=lambda c: f"{c} — {companies.COMPANIES[c]}")
if not companies.table_specs(code):
    st.info(f"{code}: ยังไม่มีข้อกำหนดการคำนวณ")
    st.stop()

skey = f"settings_{code}"
if skey not in st.session_state:
    st.session_state[skey] = companies.load_settings(code)
tables, saved_eligible = st.session_state[skey]

# ---------------------------------------------------------------- ② ตารางอัตรา
st.subheader("② อัตรา Commission")
st.caption("แก้ค่าในตารางได้เลย ค่าที่แก้ใช้กับการคำนวณรอบนี้ · กด 'บันทึกเป็นค่า default' ถ้าต้องการใช้ค่านี้ครั้งต่อไป")
edited = {}
for key, title, help_text, fixed, locked in companies.table_specs(code):
    with st.expander(title, expanded=key not in ("fsa", "new_product")):
        st.caption(help_text)
        rows = tables.get(key) or []
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EMPTY_COLUMNS.get(key, []))
        colcfg = {}
        for c in df.columns:
            if "(%)" in c or "% ของ" in c:
                colcfg[c] = st.column_config.NumberColumn(c, format="%.3f", min_value=0.0)
            elif "(บาท)" in c:
                colcfg[c] = st.column_config.NumberColumn(c, format="localized", min_value=0.0)
            elif c == "เดือน (1-12)":
                colcfg[c] = st.column_config.NumberColumn(c, min_value=1, max_value=12, step=1)
            else:
                colcfg[c] = st.column_config.TextColumn(c)
        res_df = st.data_editor(df, key=f"ed_{code}_{key}", hide_index=True, use_container_width=True,
                                num_rows="fixed" if fixed else "dynamic", disabled=locked, column_config=colcfg)
        edited[key] = clean(res_df.to_dict("records"))

# ---------------------------------------------------------------- ③ ไฟล์ยอดขาย
st.subheader("③ ไฟล์ยอดขายจากระบบ")
sales_file = st.file_uploader("ไฟล์ยอดขาย (.txt / .csv / .xlsx)", type=["txt", "csv", "xlsx"])
eligible_rows = []
if sales_file is not None:
    found = salesmen_in_file(sales_file.getvalue(), Path(sales_file.name).name,
                             cfg.get("delimiter"), cfg["columns"]["salesperson"])
    with st.expander(f"Saleman ที่มีสิทธิ์รับ Commission ({len(found)} คนในไฟล์)", expanded=False):
        st.caption("เอาเครื่องหมายออกสำหรับคนที่ไม่มีสิทธิ์ · ค่าจะถูกจำเมื่อกดบันทึกเป็นค่า default")
        el_df = pd.DataFrame([{"Saleman": s, "มีสิทธิ์": bool(saved_eligible.get(s, True))} for s in found])
        el_df = st.data_editor(el_df, key=f"el_{code}_{hashlib.md5(sales_file.getvalue()[:4096]).hexdigest()}",
                               hide_index=True, use_container_width=True, num_rows="fixed", disabled=["Saleman"])
        eligible_rows = el_df.to_dict("records")

year = st.number_input("ปีที่คำนวณ (0 = ปีล่าสุดในไฟล์)", min_value=0, max_value=2100, value=0, step=1)

b1, b2, b3 = st.columns([1, 1, 3])
run = b1.button("④ คำนวณ", type="primary", disabled=sales_file is None)
if b2.button("💾 บันทึกเป็นค่า default"):
    elig_map = dict(saved_eligible)
    elig_map.update({r["Saleman"]: bool(r["มีสิทธิ์"]) for r in eligible_rows})
    companies.save_settings(code, edited, elig_map)
    st.session_state[skey] = companies.load_settings(code)
    st.success(f"บันทึกค่า default ของ {code} แล้ว")
if b3.button("↩️ คืนค่าเริ่มต้นของระบบ"):
    companies.reset_settings(code)
    st.session_state.pop(skey, None)
    for k in [k for k in st.session_state if k.startswith(f"ed_{code}_")]:
        st.session_state.pop(k)
    st.rerun()

# ---------------------------------------------------------------- ④ คำนวณ
if run:
    eligible = {r["Saleman"] for r in eligible_rows if r["มีสิทธิ์"]} if eligible_rows else None
    with tempfile.TemporaryDirectory() as tmp, st.spinner("กำลังคำนวณ..."):
        sp = Path(tmp) / Path(sales_file.name).name
        sp.write_bytes(sales_file.getvalue())
        try:
            res = companies.compute(code, sp, cfg, edited, int(year) or None, eligible)
            buf = io.BytesIO()
            core.save_excel(res, buf)
        except SystemExit as e:
            st.error(str(e))
            st.stop()
        except Exception as e:  # ไฟล์ผิดรูปแบบ ฯลฯ
            st.error(f"คำนวณไม่สำเร็จ: {e}")
            st.stop()
    st.session_state["result"] = (code, res, buf.getvalue())

if st.session_state.get("result") and st.session_state["result"][0] == code:
    _, res, xlsx = st.session_state["result"]
    y = res["year"]
    for w in res["warnings"]:
        st.warning(w)
    total = sum(res["col_total"])
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Commission รวม {code} ปี {y}", f"฿{total:,.2f}")
    m2.metric("จำนวน Saleman", len(res["names"]))
    m3.metric("จำนวนแถวที่คำนวณ", f"{len(res['detail']):,}")
    fname = f"incentive_{code.replace(' ', '_')}_{y}.xlsx"
    st.download_button(f"⬇️ ดาวน์โหลด {fname}", xlsx, fname, type="primary",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader("Sale Summary (ตามเดือน Invoice)")
    table = [{"Saleman": n, **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["monthly"][n])},
              "Total": round(sum(res["monthly"][n]), 2)} for n in res["names"]]
    table.append({"Saleman": "Total", **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["col_total"])},
                  "Total": round(total, 2)})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={k: st.column_config.NumberColumn(format="localized")
                                for k in core.MONTH_NAMES + ["Total"]})

    st.subheader("สรุปตาม Commission Tier")
    agg = Counter()
    amt = Counter()
    for d in res["detail"]:
        agg[d["tier"]] += 1
        amt[d["tier"]] += d["incentive"]
    st.dataframe([{"Commission Tier": k, "แถว": v, "Commission (THB)": round(amt[k], 2)}
                  for k, v in agg.most_common()], hide_index=True,
                 column_config={"Commission (THB)": st.column_config.NumberColumn(format="localized")})
