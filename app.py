"""หน้าเว็บคำนวณ Sales Commission

รัน:  streamlit run app.py
ตั้งรหัสผ่าน (แนะนำ): ตั้ง environment variable APP_PASSWORD ก่อนรัน
"""
import io
import os
import tempfile
from collections import Counter
from pathlib import Path

import streamlit as st

import incentive as core
import make_rates_template

APP_DIR = Path(__file__).resolve().parent
st.set_page_config(page_title="Sales Commission", page_icon="💰", layout="wide")


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


if not check_password():
    st.stop()

cfg = core.load_config(APP_DIR / "config.yaml")
saved_rates = APP_DIR / "data" / cfg.get("rates_file", "rates.xlsx")

st.title("💰 Sales Commission")
st.caption("อัปโหลดไฟล์ยอดขายจากระบบ → คำนวณ → ดาวน์โหลด Excel")

with st.sidebar:
    st.header("ไฟล์อัตรา (rates.xlsx)")
    tpl = io.BytesIO()
    make_rates_template.build(tpl)
    st.download_button("⬇️ ดาวน์โหลด template เปล่า", tpl.getvalue(), "rates_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown(
        "**ลำดับการคิด Commission Tier**\n"
        "1. USDB / ต้นทุน 0 → NO COMMISSION\n"
        "2. Margin ต่ำกว่า MIN ของ LOW → BELOW LOW\n"
        "3. Item อยู่ในชีต New Product → NEW PRODUCT\n"
        "4. อื่น ๆ → LOW / MID / HIGH ตาม Type")

c1, c2 = st.columns(2)
with c1:
    sales_file = st.file_uploader("1) ไฟล์ยอดขายจากระบบ", type=["txt", "csv", "xlsx"])
with c2:
    rates_file = st.file_uploader("2) rates.xlsx", type=["xlsx"])
    if rates_file is None and saved_rates.exists():
        st.info("ไม่อัปโหลด = ใช้ rates.xlsx ที่เก็บไว้บนเครื่องนี้")

year = st.number_input("ปีที่คำนวณ (0 = ปีล่าสุดในไฟล์)", min_value=0, max_value=2100, value=0, step=1)

if st.button("คำนวณ", type="primary", disabled=sales_file is None):
    if rates_file is None and not saved_rates.exists():
        st.error("กรุณาอัปโหลด rates.xlsx")
        st.stop()
    with tempfile.TemporaryDirectory() as tmp, st.spinner("กำลังคำนวณ..."):
        sp = Path(tmp) / Path(sales_file.name).name
        sp.write_bytes(sales_file.getvalue())
        if rates_file is not None:
            rp = Path(tmp) / "rates.xlsx"
            rp.write_bytes(rates_file.getvalue())
        else:
            rp = saved_rates
        try:
            res = core.compute(sp, rp, cfg, int(year) or None)
            buf = io.BytesIO()
            core.save_excel(res, buf)
        except SystemExit as e:
            st.error(str(e))
            st.stop()
        except Exception as e:  # ไฟล์ผิดรูปแบบ ฯลฯ
            st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
            st.stop()
    st.session_state["result"] = (res, buf.getvalue())

if "result" in st.session_state:
    res, xlsx = st.session_state["result"]
    y, lb = res["year"], res["lookback"]
    for w in res["warnings"]:
        st.warning(w)
    total = sum(res["col_total"])
    tiers = Counter(d["tier"] for d in res["detail"])
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Commission รวมปี {y}", f"฿{total:,.2f}")
    m2.metric("จำนวน Saleman", len(res["names"]))
    m3.metric("จำนวนแถวที่คำนวณ", f"{len(res['detail']):,}")
    st.caption(f"เช็คลูกค้า/สินค้าย้อนหลังปี {y - lb}-{y - 1}")

    st.download_button(f"⬇️ ดาวน์โหลด incentive_{y}.xlsx", xlsx, f"incentive_{y}.xlsx", type="primary",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader("Sale Summary")
    table = [{"Saleman": n, **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["monthly"][n])},
              "Total": round(sum(res["monthly"][n]), 2)} for n in res["names"]]
    table.append({"Saleman": "Total", **{m: round(v, 2) for m, v in zip(core.MONTH_NAMES, res["col_total"])},
                  "Total": round(total, 2)})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={k: st.column_config.NumberColumn(format="localized")
                                for k in core.MONTH_NAMES + ["Total"]})

    st.subheader("จำนวนแถวตาม Commission Tier")
    st.dataframe([{"Commission Tier": k, "แถว": v} for k, v in tiers.most_common()], hide_index=True)
