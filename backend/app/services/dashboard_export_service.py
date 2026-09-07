import csv
import io
import json
from copy import copy
from typing import Any, Dict

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _metric_rows(dashboard: Dict[str, Any]) -> list[list[str]]:
    rows = []
    for metric in dashboard["metrics"]:
        rows.append([
            metric["label"],
            "" if metric.get("value") is None else str(metric["value"]),
            metric.get("unit") or "",
            "Available" if metric.get("available", True) else "Unavailable",
            json.dumps(metric.get("chart") or [], separators=(",", ":")),
        ])
    return rows


def build_dashboard_csv(dashboard: Dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Dashboard", dashboard.get("hospital") or dashboard.get("department") or "main"])
    writer.writerow(["Department", dashboard.get("filters", {}).get("department") or ""])
    writer.writerow(["Start date", dashboard.get("filters", {}).get("start_date") or ""])
    writer.writerow(["End date", dashboard.get("filters", {}).get("end_date") or ""])
    writer.writerow([])
    writer.writerow(["Metric", "Value", "Unit", "Status", "Chart data"])
    writer.writerows(_metric_rows(dashboard))
    return output.getvalue().encode("utf-8-sig")


def build_dashboard_xlsx(dashboard: Dict[str, Any]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dashboard"
    sheet.append(["Dashboard", dashboard.get("hospital") or dashboard.get("department") or "main"])
    sheet.append(["Department", dashboard.get("filters", {}).get("department") or ""])
    sheet.append(["Start date", dashboard.get("filters", {}).get("start_date") or ""])
    sheet.append(["End date", dashboard.get("filters", {}).get("end_date") or ""])
    sheet.append([])
    sheet.append(["Metric", "Value", "Unit", "Status", "Chart data"])
    for row in _metric_rows(dashboard):
        sheet.append(row)
    for cell in sheet[6]:
        font = copy(cell.font)
        font.bold = True
        cell.font = font
    sheet.freeze_panes = "A7"
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 16
    sheet.column_dimensions["C"].width = 12
    sheet.column_dimensions["D"].width = 16
    sheet.column_dimensions["E"].width = 60
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_dashboard_pdf(dashboard: Dict[str, Any]) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    filters = dashboard.get("filters", {})
    title = dashboard.get("hospital") or dashboard.get("department") or "main"
    elements = [Paragraph(f"Operations Dashboard: {title}", styles["Title"])]
    elements.append(Paragraph(
        f"Department: {filters.get('department') or 'All departments'} | "
        f"Start date: {filters.get('start_date') or 'Any'} | End date: {filters.get('end_date') or 'Any'}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.2 * inch))
    table_data = [["Metric", "Value", "Unit", "Status"]]
    table_data.extend([row[:4] for row in _metric_rows(dashboard)])
    table = Table(table_data, colWidths=[2.3 * inch, 1.2 * inch, 1.0 * inch, 1.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f3f6f9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elements.append(table)
    document.build(elements)
    return output.getvalue()