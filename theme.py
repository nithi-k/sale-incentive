"""ธีม/สไตล์หน้าเว็บ — โครงแบบแดชบอร์ด (เมนูซ้าย + การ์ดขาวบนพื้นเทาอ่อน) สีตาม chaiyaboon.com"""
import base64
import html
from pathlib import Path

import streamlit as st

RED = "#BA0D1B"
RED_DARK = "#8F0A15"
RED_SOFT = "#FBECEE"
INK = "#1D1B1C"
MUTED = "#6B6668"
LINE = "#ECE8E8"
CANVAS = "#F6F5F5"
LOGO_URL = ("https://images.squarespace-cdn.com/content/v1/68df43bb8116263375d38803/"
            "da531f3b-3067-4bef-b846-e74e656949ec/CHAIYABOON-02..png?format=500w")
ASSETS = Path(__file__).resolve().parent / "assets"

CSS = f"""
<style>
:root {{ --red:{RED}; --ink:{INK}; --muted:{MUTED}; --line:{LINE}; }}
html, body, .stApp, button, input, textarea, [data-testid="stMarkdownContainer"] {{
    font-family: "Inter", Arial, Helvetica, "Sukhumvit Set", "Leelawadee UI", sans-serif;
}}
.stApp {{ background: {CANVAS}; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
.block-container {{ max-width: 1180px; padding: 2rem 2.2rem 3rem; }}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid {LINE}; width: 260px !important; }}
section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] > div {{ padding-top: 1.2rem; }}
.side-logo {{ padding: .1rem .2rem 1rem; border-bottom:1px solid {LINE}; margin-bottom: .6rem; }}
.logo-box {{ position:relative; display:inline-block; height:38px; min-width:150px; }}
.logo-box .alt {{ position:absolute; left:0; top:50%; transform:translateY(-50%); font-weight:800; color:{RED};
    letter-spacing:.08em; font-size:1.1rem; white-space:nowrap; }}
.logo-box img {{ position:relative; height:38px; background:#fff; border-radius:999px; }}
.side-label {{ font-size:.7rem; font-weight:600; color:#A39C9E; letter-spacing:.08em; text-transform:uppercase; margin: .9rem 0 .35rem .35rem; }}
section[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; width: 100%; }}
section[data-testid="stSidebar"] [role="radiogroup"] > div {{ width: 100%; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{ display: flex; box-sizing: border-box; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
    padding: .5rem .7rem; border-radius: 10px; width: 100%; margin: 0; cursor: pointer;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child,
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}
section[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size: .9rem; color: {INK}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: {CANVAS}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
section[data-testid="stSidebar"] label[data-selected="true"] {{ background: {RED_SOFT}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p,
section[data-testid="stSidebar"] label[data-selected="true"] p {{ color: {RED}; font-weight: 600; }}
[data-testid="stSidebarHeader"] {{ height: 1.2rem; min-height: 0; padding: 0; }}
.side-help {{ font-size:.78rem; color:{MUTED}; line-height:1.55; padding: 0 .35rem; }}
.side-help b {{ color:{INK}; }}

/* ---------- page head ---------- */
.crumb {{ font-size:.8rem; color:{MUTED}; margin-bottom:.35rem; }}
.crumb b {{ color:{INK}; font-weight:500; }}
.page-title {{ font-size:2rem; font-weight:700; color:{INK}; margin:0; line-height:1.15; letter-spacing:-.01em; }}
.page-meta {{ font-size:.85rem; color:{MUTED}; margin:.35rem 0 1.2rem; }}
.page-meta .dot {{ display:inline-block; width:4px; height:4px; border-radius:50%; background:#C9C3C4; margin:0 .5rem 2px; }}

/* ---------- cards ---------- */
[class*="st-key-card"] {{
    background:#fff; border:1px solid {LINE} !important; border-radius:16px; padding:18px 20px !important;
    box-shadow: 0 1px 2px rgba(29,27,28,.03);
}}
.card-title {{ font-size:1rem; font-weight:600; color:{INK}; margin:0; }}
.card-sub {{ font-size:.8rem; color:{MUTED}; margin:.15rem 0 .6rem; }}

/* ---------- KPI ---------- */
.kpis {{ display:grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: .2rem 0 1rem; }}
.kpi {{ background:#fff; border:1px solid {LINE}; border-radius:16px; padding:16px 18px; }}
.kpi .k {{ font-size:.78rem; color:{MUTED}; }}
.kpi .v {{ font-size:1.55rem; font-weight:700; color:{INK}; margin-top:.25rem; letter-spacing:-.01em; }}
.kpi.main {{ background:{RED}; border-color:{RED}; }}
.kpi.main .k {{ color:rgba(255,255,255,.8); }} .kpi.main .v {{ color:#fff; }}
@media (max-width: 900px) {{ .kpis {{ grid-template-columns: repeat(2, 1fr); }} }}

/* ---------- tabs = pill ---------- */
[role="tablist"] {{ gap:4px; background:{CANVAS}; padding:4px; border-radius:12px; width:fit-content; max-width:100%;
    flex-wrap:wrap; border:none !important; box-shadow:none !important; }}
[role="tablist"] [role="tab"] {{ height:auto; padding:.4rem .95rem; border-radius:9px; font-size:.85rem; color:{MUTED};
    border:none !important; background:transparent; }}
[role="tablist"] [role="tab"] p {{ font-size:.85rem; }}
[role="tablist"] [role="tab"][aria-selected="true"] {{ background:#fff; color:{INK}; box-shadow:0 1px 2px rgba(0,0,0,.08); }}
[role="tablist"] [role="tab"][aria-selected="true"] p {{ color:{INK}; font-weight:600; }}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"], [role="tablist"] > div:not([role="tab"]),
[role="tablist"] [role="tab"]::after, [role="tablist"] [role="tab"] > div:not([data-testid]) {{ display:none !important; }}
[role="tablist"] [role="tab"][aria-selected="true"] {{ border-bottom: none !important; }}
[role="tabpanel"] {{ padding-top: .6rem; }}

/* horizontal radio = pill filter */
.main [role="radiogroup"][aria-orientation="horizontal"], [data-testid="stMain"] div[role="radiogroup"] {{ gap:6px; flex-wrap:wrap; }}
[data-testid="stMain"] div[role="radiogroup"] label {{
    border:1px solid {LINE}; border-radius:999px; padding:.25rem .8rem; margin:0; background:#fff;
}}
[data-testid="stMain"] div[role="radiogroup"] label > div:first-child,
[data-testid="stMain"] label[data-testid="stRadioOption"] > div > div:first-child {{ display:none; }}
[data-testid="stMain"] div[role="radiogroup"] label p {{ font-size:.8rem; color:{MUTED}; }}
[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked),
[data-testid="stMain"] label[data-selected="true"] {{ background:{INK}; border-color:{INK}; }}
[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) p,
[data-testid="stMain"] label[data-selected="true"] p {{ color:#fff; }}

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {{
    border-radius:10px; padding:.45rem 1rem; font-weight:500; font-size:.85rem;
    border:1px solid {LINE}; color:{INK}; background:#fff; box-shadow:0 1px 1px rgba(0,0,0,.03);
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:{RED}; color:{RED}; background:#fff; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ background:{RED}; color:#fff; border-color:{RED}; }}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{ background:{RED_DARK}; color:#fff; }}
.stButton > button:disabled {{ background:#F1EEEE; color:#B5AEB0; border-color:{LINE}; }}

/* ---------- inputs ---------- */
[data-testid="stFileUploaderDropzone"] {{ border-radius:12px; background:{CANVAS}; border:1px dashed #D8D2D3; }}
[data-baseweb="input"], [data-baseweb="select"] > div {{ border-radius:10px !important; }}
[data-testid="stExpander"] details {{ border-radius:12px; border-color:{LINE}; background:#fff; }}
[data-testid="stAlert"] {{ border-radius:12px; }}

/* ---------- login ---------- */
.login-head {{ text-align:center; margin: 1rem 0 1.2rem; }}
.login-head .logo-box {{ height:54px; min-width:190px; }}
.login-head .logo-box img {{ height:54px; }}
.login-head .logo-box .alt {{ left:50%; transform:translate(-50%,-50%); font-size:1.35rem; }}
.login-head h1 {{ font-size:1.45rem; font-weight:700; color:{INK}; margin:.9rem 0 .2rem; padding:0; }}
.login-head p {{ color:{MUTED}; font-size:.85rem; margin:0; }}
.login-bar {{ height:5px; border-radius:5px; background:linear-gradient(90deg,{RED_DARK},{RED},#E0424C); margin-bottom:.8rem; }}

.foot {{ color:#A39C9E; font-size:.75rem; text-align:center; margin-top:2.5rem; }}
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


def logo_src():
    """ใช้ไฟล์โลโก้ใน assets/ ถ้ามี (ใช้ได้แม้ไม่มีอินเทอร์เน็ต) ไม่งั้นโหลดจากเว็บไซต์บริษัท"""
    for name, mime in (("cbg-logo.png", "image/png"), ("cbg-logo.webp", "image/webp")):
        f = ASSETS / name
        if f.exists():
            return f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"
    return LOGO_URL


def _logo():
    src = logo_src()
    if src.startswith("data:"):  # มีไฟล์โลโก้ในเครื่อง — แสดงรูปอย่างเดียว
        return f'<span class="logo-box"><img src="{src}" alt="CHAIYABOON"></span>'
    # โหลดจากเว็บ: ข้อความ CHAIYABOON อยู่ใต้รูป — ถ้าโหลดรูปไม่ได้ (ออฟไลน์) จะเห็นข้อความแทน
    return f'<span class="logo-box"><span class="alt">CHAIYABOON</span><img src="{src}" alt=""></span>'


def sidebar_logo():
    st.sidebar.markdown(f'<div class="side-logo">{_logo()}</div>', unsafe_allow_html=True)


def side_label(text):
    st.sidebar.markdown(f'<div class="side-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def side_help(md_html):
    st.sidebar.markdown(f'<div class="side-help">{md_html}</div>', unsafe_allow_html=True)


def login_head(title, sub):
    st.markdown(f'<div class="login-bar"></div><div class="login-head">{_logo()}'
                f'<h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div>', unsafe_allow_html=True)


def page_head(crumbs, title, meta):
    crumb = " / ".join(f"<b>{html.escape(c)}</b>" if i == len(crumbs) - 1 else html.escape(c)
                       for i, c in enumerate(crumbs))
    meta_html = '<span class="dot"></span>'.join(html.escape(m) for m in meta if m)
    st.markdown(f'<div class="crumb">{crumb}</div><div class="page-title">{html.escape(title)}</div>'
                f'<div class="page-meta">{meta_html}</div>', unsafe_allow_html=True)


def card_head(title, sub=""):
    st.markdown(f'<div class="card-title">{html.escape(title)}</div>'
                + (f'<div class="card-sub">{html.escape(sub)}</div>' if sub else ""), unsafe_allow_html=True)


def kpis(items):
    """items = [(label, value, main?)]"""
    cells = "".join(f'<div class="kpi{" main" if main else ""}"><div class="k">{html.escape(k)}</div>'
                    f'<div class="v">{html.escape(v)}</div></div>' for k, v, main in items)
    st.markdown(f'<div class="kpis">{cells}</div>', unsafe_allow_html=True)


COMPANY_LOGOS = {  # ไฟล์ใน assets/ (ดาวน์โหลดจาก chaiyaboon.com)
    "CBG": "cbg-logo.png", "SAS": "logo-SAS.jpg", "CM": "logo-CM.jpg",
    "DAP UV": "logo-DAP_UV.jpg", "SC": "logo-SC.jpg",
}


def _data_uri(path):
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def company_nav_css(codes):
    """ใส่โลโก้บริษัทหน้าชื่อในเมนูซ้าย (ตามลำดับตัวเลือกของ radio) + ตัวย่อบริษัทใต้ชื่อ"""
    rules = []
    for i, code in enumerate(codes, start=1):
        # ตัวเลือก radio แต่ละอันถูกห่อด้วย div แยกกัน จึงจับจากค่าของ input (0, 1, 2, ...) แทนลำดับ label
        sels = [f'section[data-testid="stSidebar"] [role="radiogroup"] label:has(input[value="{i - 1}"]) p',
                f'section[data-testid="stSidebar"] [role="radiogroup"] > div:nth-child({i}) label p']
        f = ASSETS / COMPANY_LOGOS.get(code, "")
        logo = f"background-image:url('{_data_uri(f)}');" if f.is_file() else ""
        rules.append(", ".join(f"{x}::before" for x in sels) + f" {{ {logo} }}")
        rules.append(", ".join(f"{x}::after" for x in sels) + f' {{ content:"{code}"; }}')
    st.markdown(f"""<style>
section[data-testid="stSidebar"] [role="radiogroup"] label p {{
    position:relative; padding-left:54px; min-height:36px; display:flex; flex-direction:column; justify-content:center;
    line-height:1.2; }}
section[data-testid="stSidebar"] [role="radiogroup"] label p::before {{
    content:""; position:absolute; left:0; top:50%; transform:translateY(-50%); width:44px; height:32px;
    border-radius:8px; background-color:#fff; border:1px solid {LINE};
    background-size:contain; background-repeat:no-repeat; background-position:center; }}
section[data-testid="stSidebar"] [role="radiogroup"] label p::after {{
    font-size:.7rem; color:#A39C9E; font-weight:500; margin-top:2px; letter-spacing:.04em; }}
section[data-testid="stSidebar"] [role="radiogroup"] label[data-selected="true"] p::before,
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p::before {{ border-color:{RED}; }}
{chr(10).join(rules)}
</style>""", unsafe_allow_html=True)


def footer():
    st.markdown('<div class="foot">© Chaiyaboon Brothers Group · Sales Commission</div>', unsafe_allow_html=True)
