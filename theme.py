"""ธีมหน้าเว็บให้ตรงกับ chaiyaboon.com — แดง #BA0D1B, ตัวอักษร #1D1B1C, ปุ่มทรง pill, Arial"""
import base64
from pathlib import Path

import streamlit as st

RED = "#BA0D1B"
RED_DARK = "#8F0A15"
INK = "#1D1B1C"
LIGHT = "#FAFAFA"
LOGO_URL = ("https://images.squarespace-cdn.com/content/v1/68df43bb8116263375d38803/"
            "da531f3b-3067-4bef-b846-e74e656949ec/CHAIYABOON-02..png?format=500w")

CSS = f"""
<style>
html, body, [class*="css"], .stMarkdown, button, input, textarea {{
    font-family: Arial, Helvetica, "Sukhumvit Set", "Thonburi", "Leelawadee UI", sans-serif;
}}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}
header[data-testid="stHeader"] {{ background: transparent; }}

/* แถบหัวสีแดงแบบเว็บไซต์บริษัท */
.cbg-banner {{
    background: radial-gradient(120% 140% at 85% 0%, #D8323C 0%, {RED} 55%, {RED_DARK} 100%);
    border-radius: 18px; padding: 22px 30px; margin-bottom: 1.4rem;
    display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap;
}}
.cbg-banner img {{ height: 58px; color: {LIGHT}; font-weight: 700; font-size: 1.5rem; letter-spacing: .08em; }}
.cbg-banner .cbg-title {{ color: {LIGHT}; text-align: right; }}
.cbg-banner .cbg-title h1 {{ color: {LIGHT}; font-size: 1.9rem; font-weight: 400; margin: 0; padding: 0; }}
.cbg-banner .cbg-title p {{ color: rgba(250,250,250,.9); margin: .3rem 0 0; font-size: .95rem; }}

/* หัวข้อขั้นตอน */
h2, h3, [data-testid="stHeadingWithActionElements"] h3 {{ color: {RED}; font-weight: 600; }}

/* ปุ่มทรง pill */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 300px; padding: .55rem 1.6rem; font-weight: 600; letter-spacing: .02em;
    border: 1.5px solid {RED}; color: {RED}; background: #fff; transition: all .15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ background: {RED}; color: {LIGHT}; border-color: {RED}; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
    background: {RED}; color: {LIGHT}; border-color: {RED};
}}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
    background: {RED_DARK}; border-color: {RED_DARK}; color: {LIGHT};
}}

/* กล่องตาราง / expander */
[data-testid="stExpander"] details {{ border-radius: 14px; border-color: #E8E3E3; }}
[data-testid="stExpander"] summary p {{ font-weight: 600; color: {INK}; }}
[data-testid="stFileUploaderDropzone"] {{ border-radius: 14px; }}

/* ตัวเลขสรุป */
[data-testid="stMetric"] {{ background: {LIGHT}; border-left: 4px solid {RED}; border-radius: 12px; padding: 14px 18px; }}
[data-testid="stMetricValue"] {{ color: {RED}; }}

.cbg-footer {{ color: rgba(29,27,28,.5); font-size: .8rem; text-align: center; margin-top: 3rem; }}
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


ASSETS = Path(__file__).resolve().parent / "assets"


def logo_src():
    """ใช้ไฟล์โลโก้ใน assets/ ถ้ามี (ใช้ได้แม้ไม่มีอินเทอร์เน็ต) ไม่งั้นโหลดจากเว็บไซต์บริษัท"""
    for name, mime in (("cbg-logo.png", "image/png"), ("cbg-logo.webp", "image/webp")):
        f = ASSETS / name
        if f.exists():
            return f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"
    return LOGO_URL


def banner(title="Sales Commission", subtitle=""):
    st.markdown(
        f'<div class="cbg-banner"><img src="{logo_src()}" alt="CHAIYABOON">'
        f'<div class="cbg-title"><h1>{title}</h1><p>{subtitle}</p></div></div>',
        unsafe_allow_html=True)


def footer():
    st.markdown('<div class="cbg-footer">© Chaiyaboon Brothers Group · Sales Commission</div>',
                unsafe_allow_html=True)
