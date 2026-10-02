"""สร้างไฟล์ rates.xlsx (ตารางอัตรา Incentive ตาม Type x Margin) แบบว่าง ให้กรอกช่องสีเหลือง
Usage: python make_rates_template.py [rates.xlsx]
"""
import sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side

YELLOW = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def build(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Rates"
    ws["A1"] = "อัตรา Incentive ตาม Type และ Margin"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("กรอกเฉพาะช่องสีเหลือง  •  Margin ตั้งแต่ (≥) / น้อยกว่า (<) กรอกเป็น %  "
                "•  เว้นว่างช่วงล่างสุด/บนสุด = ไม่จำกัด")
    ws["A2"].font = Font(italic=True, color="666666")

    rows = [("TYPE/MARGIN", ["< 20%", "20-40%", ">40%"]),
            ("Margin ตั้งแต่ (≥)", [None] * 3),
            ("Margin น้อยกว่า (<)", [None] * 3),
            ("OCOP", [None] * 3),
            ("OCNP", [None] * 3),
            ("NC", [None] * 3)]
    for i, (label, vals) in enumerate(rows, start=4):
        a = ws.cell(row=i, column=1, value=label)
        a.font = Font(bold=True)
        a.border = BOX
        a.alignment = Alignment(horizontal="center")
        for j, v in enumerate(vals, start=2):
            c = ws.cell(row=i, column=j, value=v)
            c.fill = YELLOW
            c.border = BOX
            c.alignment = Alignment(horizontal="center")
            c.protection = Protection(locked=False)
            if i == 4:
                c.font = Font(bold=True)
            else:
                c.number_format = "0.00%"
    ws.column_dimensions["A"].width = 22
    for col in "BCD":
        ws.column_dimensions[col].width = 14
    ws.protection.sheet = True  # แก้ได้เฉพาะช่องสีเหลือง (ไม่มีรหัสผ่าน)
    wb.save(path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "rates.xlsx"
    build(out)
    print(f"สร้าง {out} แล้ว — กรอกช่องสีเหลืองให้ครบก่อนรัน incentive.py")
