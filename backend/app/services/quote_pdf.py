"""
quote_pdf.py - Makes the PDF quotation (ReportLab): the three options side by side,
a cost breakdown of the recommended system, a usage-vs-solar chart and the assumptions.
"""
import io
from datetime import timedelta

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import config

NAMES = {"on_grid": "On-grid", "hybrid": "Hybrid (with battery)", "off_grid": "Off-grid"}
SHORT = {"on_grid": "On-grid", "hybrid": "Hybrid + battery", "off_grid": "Off-grid"}
ITEM_NAMES = {"panels": "Solar panels", "inverter": "Inverter", "batteries": "Lithium batteries",
              "structure": "Mounting structure", "installation": "Wiring, protection & labour",
              "net_billing": "Green meter + DISCO approval", "margin": "Installer margin"}
SUN = colors.HexColor("#f59e0b")
INK = colors.HexColor("#0f2a3d")


def rs(value) -> str:
    return f"Rs {value:,.0f}" if value is not None else "-"


def _table(data, widths, highlight_col=None):
    t = Table(data, colWidths=widths)
    style = [("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if highlight_col is not None:
        style += [("BACKGROUND", (highlight_col, 1), (highlight_col, -1), colors.HexColor("#fff7e6")),
                  ("FONTNAME", (highlight_col, 1), (highlight_col, -1), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def _chart(option):
    d = Drawing(170 * mm, 62 * mm)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 12 * mm, 10 * mm, 150 * mm, 45 * mm
    chart.data = [[m["used"] for m in option["months"]], [m["generated"] for m in option["months"]]]
    chart.categoryAxis.categoryNames = [m["month"] for m in option["months"]]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.bars[0].fillColor = colors.HexColor("#94a3b8")
    chart.bars[1].fillColor = SUN
    chart.barSpacing, chart.groupSpacing = 1, 5
    d.add(chart)
    d.add(String(12 * mm, 58 * mm, "Units per month:  grey = you use   orange = solar makes", fontSize=8,
                 fillColor=INK))
    return d


def _outage_text(result):
    outage = result["inputs"].get("outage")
    if outage:
        return outage["text"].lower() if outage["days_per_week"] else "none"
    return f"{result['inputs'].get('outage_hours', 0):g} h/day"


def make_quote_pdf(quote: dict) -> bytes:
    result = quote["result"]
    options = result["options"]
    pick = result["recommended"]
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#475569"))
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"Solar quotation Q-{quote['quote_id']:05d}")
    created = quote["created_at"]
    story = [
        Paragraph(f"<font color='#f59e0b'>Solar</font> quotation - {config.INSTALLER_NAME}", styles["Title"]),
        Paragraph(f"Quotation <b>Q-{quote['quote_id']:05d}</b> &nbsp;|&nbsp; {created:%d %b %Y} &nbsp;|&nbsp; "
                  f"valid until {created + timedelta(days=config.QUOTE_VALID_DAYS):%d %b %Y}"
                  + (f" &nbsp;|&nbsp; for {quote['customer_name']}" if quote.get("customer_name") else ""),
                  styles["Normal"]),
        Spacer(1, 5 * mm),
        Paragraph(f"Your home: <b>{result['inputs']['average_units']} units/month</b> in "
                  f"{result['inputs']['city'].title()}, current bill about <b>{rs(result['current_bill']['total'])}"
                  f"</b>/month, load-shedding: {_outage_text(result)}.", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]
    kinds = ["on_grid", "hybrid", "off_grid"]
    rows = [["", *[SHORT[k] + ("\nRECOMMENDED" if k == pick else "") for k in kinds]]]
    for label, get in [
        ("System size", lambda o: f"{o['system_kw']:g} kW"),
        ("Panels", lambda o: f"{o['panels']} x {o['panel_watt']} W"),
        ("Inverter", lambda o: f"{o['inverter_kw']} kW"),
        ("Battery", lambda o: f"{o['battery_kwh']:g} kWh (~{o['backup_hours']:g} h backup)" if o["battery_kwh"] else "-"),
        ("Roof space", lambda o: f"~{o['roof_sqft']:,} sq ft"),
        ("Total price", lambda o: rs(o["cost"]["total"])),
        ("Bill after solar", lambda o: rs(o.get("monthly_bill_after"))),
        ("Saving per month", lambda o: rs(o["monthly_saving"])),
        ("Works in load-shedding", lambda o: "Yes" if o.get("works_in_load_shedding", o["kind"] != "on_grid")
         else "No (switches off)"),
        ("Payback", lambda o: f"{o['payback_years']:g} years" if o["payback_years"] else "-"),
        ("Saving in 25 years", lambda o: rs(o["saving_25_years"])),
        ("CO2 avoided", lambda o: f"{o['co2_tonnes_per_year']:g} t/year"),
    ]:
        rows.append([label, *[get(options[k]) for k in kinds]])
    story += [_table(rows, [38 * mm, 48 * mm, 48 * mm, 44 * mm], highlight_col=kinds.index(pick) + 1),
              Spacer(1, 3 * mm),
              Paragraph(f"<b>Why {NAMES[pick]}?</b> {result['reason']}", styles["Normal"])]
    for note in result["notes"]:
        story.append(Paragraph(f"Note: {note}", small))

    best = options[pick]
    story += [Spacer(1, 5 * mm), Paragraph(f"Price breakdown: {NAMES[pick]}", styles["Heading3"]),
              _table([["Item", "Price"]] + [[ITEM_NAMES[k], rs(v)] for k, v in best["cost"]["items"].items() if v]
                     + [["Total", rs(best["cost"]["total"])]], [110 * mm, 40 * mm]),
              Spacer(1, 5 * mm), _chart(best)]
    if best.get("scenarios"):
        rows = [["Your monthly bill if you choose...", "Bill / month", "Payback"]]
        for k in kinds:
            for sc in options[k]["scenarios"]:
                rows.append([f"{SHORT[k]}: {sc['label']}", rs(sc["monthly_bill"]),
                             f"{sc['payback_years']:g} yr" if sc["payback_years"] else "-"])
        story += [Spacer(1, 4 * mm), Paragraph("WAPDA connection: every choice", styles["Heading3"]),
                  _table(rows, [120 * mm, 28 * mm, 26 * mm])]
    if result.get("packages"):
        story += [Spacer(1, 4 * mm), Paragraph(f"Packages for the {NAMES[pick]} system", styles["Heading3"]),
                  _table([["Package", "Parts (examples)", "Price"]] +
                         [[p["label"], Paragraph(p["parts"] + "<br/>" + p["warranty"], small), rs(p["total"])]
                          for p in result["packages"]], [24 * mm, 122 * mm, 28 * mm])]
    if result.get("financing"):
        f = result["financing"]
        story += [Spacer(1, 3 * mm), Paragraph(
            f"Instalments (example, {f['markup_percent']:g}% yearly markup, down payment {rs(f['down_payment'])}): "
            + "; ".join(f"{p['months']} months {rs(p['monthly'])}/month" for p in f["plans"]) + ".", small)]
    a = result["assumptions"]
    story += [Spacer(1, 3 * mm), Paragraph(
        f"Assumptions: {a['yield_kwh_per_kw_year']:,} units per kW per year "
        f"({a.get('sunlight_source', 'city average')}); panels Rs "
        f"{a['panel_price_per_watt']:g}/W; lithium battery Rs {a['battery_per_kwh']:,.0f}/kWh; net-billing export "
        f"Rs {a['export_rate']:g}/unit; bills from the NEPRA domestic tariff (Feb 2026) without FPA/QTA. "
        f"This is an estimate: the final price is confirmed after a free site survey. Call {config.INSTALLER_PHONE}. "
        "Portfolio demo - not a real offer.", small)]
    doc.build(story)
    return buffer.getvalue()
