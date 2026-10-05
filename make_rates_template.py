"""สร้างไฟล์ rates.xlsx (อัตรา Commission ตาม Type x Margin Tier) แบบว่าง ให้กรอกช่องสีเหลือง
Usage: python make_rates_template.py [data/rates.xlsx]
ไม่เขียนทับไฟล์ที่มีอยู่แล้ว (กันอัตราที่กรอกไว้หาย)
"""
import sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side

TIERS = ["LOW", "MID", "HIGH"]
TYPES = ["OCOP", "OCNP", "NC"]
YELLOW = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def cell(ws, r, c, v=None, bold=False, inp=False, pct=False):
    x = ws.cell(row=r, column=c, value=v)
    x.border = BOX
    x.alignment = Alignment(horizontal="center")
    if bold:
        x.font = Font(bold=True)
    if inp:
        x.fill = YELLOW
        x.protection = Protection(locked=False)
    if pct:
        x.number_format = "0.00%"
    return x


def build(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Rates"
    # ตาราง 1: Commission % ตาม Type x Tier
    cell(ws, 1, 1, "TYPE/MARGIN", bold=True)
    for j, t in enumerate(TIERS, start=2):
        cell(ws, 1, j, t)
    for i, ty in enumerate(TYPES, start=2):
        cell(ws, i, 1, ty)
        for j in range(2, 2 + len(TIERS)):
            cell(ws, i, j, inp=True, pct=True)
    # ตาราง 2: MIN Margin ของแต่ละ Tier
    r0 = 3 + len(TYPES)
    cell(ws, r0, 1, "MARGIN TYPE", bold=True)
    cell(ws, r0, 2, "MIN")
    for i, t in enumerate(TIERS, start=r0 + 1):
        cell(ws, i, 1, t).alignment = Alignment(horizontal="left")
        cell(ws, i, 2, inp=True, pct=True)
    ws["F1"] = "กรอกเฉพาะช่องสีเหลือง"
    ws["F2"] = "Tier = MIN สูงสุดที่ Margin ถึง (Margin ≥ MIN)"
    ws["F3"] = "Margin ต่ำกว่า MIN ของ Tier ต่ำสุด = ไม่ได้ Commission"
    for c in ("F1", "F2", "F3"):
        ws[c].font = Font(italic=True, color="666666")
    ws.column_dimensions["A"].width = 16
    for col in "BCD":
        ws.column_dimensions[col].width = 12
    ws.protection.sheet = True  # แก้ได้เฉพาะช่องสีเหลือง (ไม่มีรหัสผ่าน)
    wb.save(path)


if __name__ == "__main__":
    from pathlib import Path
    out = sys.argv[1] if len(sys.argv) > 1 else "data/rates.xlsx"
    if Path(out).exists():
        sys.exit(f"มีไฟล์ {out} อยู่แล้ว — ไม่เขียนทับ (ลบหรือเปลี่ยนชื่อไฟล์เดิมก่อน)")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    build(out)
    print(f"สร้าง {out} แล้ว — กรอกช่องสีเหลืองให้ครบก่อนรัน incentive.py")
