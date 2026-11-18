from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


HEADERS = ["ID", "Дата", "Файл", "Тип", "Транспорт", "Нарушения", "Красный", "Время, с"]


def rows(records):
    return [
        [r["id"], r["timestamp"], r["original_filename"], r["media_type"], r["vehicle_count"],
         r["violation_count"], "да" if r["red_light"] else "нет", r["processing_time"]]
        for r in records
    ]


def export_history_to_excel(records, output_dir):
    output_dir = Path(output_dir)
    path = output_dir / "red_light_history.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "История"
    sheet.append(HEADERS)
    for row in rows(records):
        sheet.append(row)

    fill = PatternFill("solid", fgColor="315E9E")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")
    widths = [8, 21, 30, 13, 14, 14, 12, 12]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    sheet.freeze_panes = "A2"
    workbook.save(path)
    return path


def export_history_to_pdf(records, output_dir):
    output_dir = Path(output_dir)
    path = output_dir / "red_light_history.pdf"
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("ReportFont", str(font_path)))
        pdfmetrics.registerFont(TTFont("ReportFontBold", str(bold_path)))
        font_name, bold_name = "ReportFont", "ReportFontBold"
    else:
        font_name = bold_name = "Helvetica"

    document = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm,
                                 topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    styles["Title"].fontName = bold_name
    styles["Normal"].fontName = font_name
    elements = [Paragraph("Отчёт по обработке файлов", styles["Title"]),
                Paragraph(f"Сформирован: {datetime.now():%d.%m.%Y %H:%M}", styles["Normal"]), Spacer(1, 8)]
    data = [HEADERS] + rows(records)
    table = Table(data, repeatRows=1, colWidths=[13*mm, 34*mm, 55*mm, 24*mm, 27*mm, 27*mm, 22*mm, 23*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315E9E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), bold_name),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3F8")]),
    ]))
    elements.append(table)
    document.build(elements)
    return path
