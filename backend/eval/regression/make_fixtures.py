"""Regenerate the regression fixtures in eval/regression/fixtures/: one small document per source
type, rebuilt from the 8 October 2026 regression report (Aurora Quay PDF, Sable Ridge DOCX,
Ember Canal Markdown, Mont Rivière Latin-1 TXT, Tidal Grid CSV, plus an HTML standards page).

Each one is padded with unrelated sections, so a question needing three distant sections can't
be answered by the top few passages alone, which is how the report's failures happened.

Run with:  uv run --with reportlab python -m eval.regression.make_fixtures
"""

import csv
import io
from pathlib import Path

import docx
from docx.shared import Pt

OUT = Path(__file__).with_name("fixtures")


# ---------- PDF: Aurora Quay (3 pages; ReportLab's default metadata title is "(anonymous)") ----------

def make_pdf() -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13)
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18)

    def bullets(items):
        return ListFlowable([ListItem(Paragraph(i, body)) for i in items], bulletType="bullet")

    story = [
        Paragraph("Aurora Quay Berth Allocation Plan 2026", h1),
        Paragraph("This plan sets out how the 1,200 berth-hours available each week at Aurora Quay are "
                  "shared between vessel classes, and what crews do when something goes wrong.", body),
        Paragraph("Weekly allocation", h2),
        Paragraph("The weekly berth-hours are allocated as follows:", body),
        bullets(["Passenger ferries: 480 berth-hours", "Fishing fleet: 360 berth-hours",
                 "Cargo coasters: 240 berth-hours", "Maintenance and dredging: 120 berth-hours"]),
        Paragraph("Unused ferry hours are released to the fishing fleet at 18:00 on the previous day.", body),
        PageBreak(),
        Paragraph("Berth rules", h2),
        bullets(["Berth 1 is reserved for passenger ferries between 06:00 and 22:00.",
                 "Berths 2 and 3 take the fishing fleet; vessels over 24 metres use Berth 3 only.",
                 "Cargo coasters use Berth 4 and must give 12 hours' notice of arrival."]),
        Paragraph("Fees", h2),
        Paragraph("The standard fee is 85 euros per berth-hour. Fishing vessels registered in Aurora "
                  "pay 60 euros per berth-hour.", body),
        PageBreak(),
        Paragraph("Emergency procedures", h2),
        Paragraph("If fire is reported on a moored vessel:", body),
        bullets(["Sound the quay siren (three long blasts).", "Clear Berths adjacent to the vessel.",
                 "Call the harbour fire team on channel 16.", "Muster all quay staff at the North Gate."]),
        Paragraph("If an oil spill is seen, deploy the boom stored at Berth 4 and inform the harbour "
                  "master within 15 minutes.", body),
    ]
    out = io.BytesIO()
    SimpleDocTemplate(out, pagesize=A4).build(story)      # no title= on purpose: tests the fallback
    (OUT / "aurora_quay.pdf").write_bytes(out.getvalue())


# ---------- DOCX: Sable Ridge (Title/Heading styles, a table, page header and footer) ----------

def make_docx() -> None:
    d = docx.Document()
    section = d.sections[0]
    section.header.paragraphs[0].text = "Sable Ridge Mining Co. - Controlled copy"
    section.footer.paragraphs[0].text = "Document SR-SP-07 revision 3. Next review due March 2027."
    d.add_heading("Sable Ridge Tunnel Gas Safety Procedure", level=0)
    d.add_paragraph("This procedure applies to every shift working in the Sable Ridge haulage tunnel.")
    d.add_heading("Gas monitoring", level=1)
    d.add_paragraph("Methane is measured at the tunnel face at the start of each shift and every two hours.")
    d.add_paragraph("If methane reaches 1.0%, stop hot work and repeat the measurement after five minutes.")
    d.add_paragraph("If methane reaches 1.5% or more, shut down all machinery immediately and evacuate "
                    "the face to the refuge station.")
    d.add_heading("Exposure limits", level=1)
    table = d.add_table(rows=1, cols=3)
    for cell, text in zip(table.rows[0].cells, ("Gas", "Action level", "Evacuation level")):
        cell.text = text
    for row in (("Methane", "1.0%", "1.5%"), ("Carbon monoxide", "30 ppm", "100 ppm"),
                ("Hydrogen sulphide", "5 ppm", "10 ppm")):
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    d.add_heading("Responsibilities", level=1)
    for text in ("The shift supervisor records every reading in the gas log.",
                 "The ventilation officer checks the main fan daily.",
                 "Every worker carries a personal gas detector."):
        d.add_paragraph(text, style="List Bullet")
    d.add_heading("Re-entry", level=1)
    d.add_paragraph("After an evacuation, nobody re-enters the face until two consecutive readings, "
                    "taken ten minutes apart, are below the action level.")
    for p in d.paragraphs:
        for run in p.runs:
            run.font.size = run.font.size or Pt(11)
    out = io.BytesIO()
    d.save(out)
    (OUT / "sable_ridge.docx").write_bytes(out.getvalue())


# ---------- Markdown: Ember Canal (three distant sections answer one compound question) ----------

EMBER_CANAL = """\
# Ember Canal Lock Operations Guide

## Overview

The Ember Canal runs 31 km from Calder Basin to the Ember estuary through nine locks. This guide is
for lock keepers on duty at Lock 5 (Heron Lock), the deepest lock on the canal.

## Lock dimensions

| Lock | Length (m) | Width (m) | Rise (m) |
|------|-----------:|----------:|---------:|
| Lock 4 | 22.0 | 4.3 | 2.1 |
| Lock 5 (Heron) | 26.5 | 4.6 | 3.8 |
| Lock 6 | 22.0 | 4.3 | 1.9 |

## Opening hours

Locks are operated from 08:00 to 19:00 between April and October, and from 09:00 to 16:00 in winter.

## Water conservation rules

When the canal authority declares a conservation order, lock keepers limit Heron Lock to 12 cycles
a day, use the side pond for every cycle, and only work the lock for leisure boats in groups of at
least three.

## Towpath maintenance

The towpath is mown every three weeks in summer. Report fallen trees to the maintenance depot.

## Visitor moorings

Visitor moorings above Heron Lock are limited to 48 hours. Boats must not moor on the lock landing.

## Back-pump failure

If the Heron back-pump fails, close the upper paddles, start the standby pump within 20 minutes,
and record the fault code from the pump panel in the lock log.

## Ice and frost

Do not operate the lock when ice is more than 2 cm thick on the pound above.

## Fees and licences

Every boat needs a current canal licence. Short-term visitor licences cost 15 pounds per day.

## Alert levels

An amber alert means a pound is falling faster than 10 cm an hour: stop all leisure lockings and
phone the duty engineer. A red alert means a breach is suspected: close every gate and paddle.

## Barge in the chamber during an alert

If a barge is inside the lock chamber when an alert is raised, keep both gates closed, hold the
chamber level steady, and secure the barge with two lines fore and two lines aft.

## Telemetry configuration

```
station = heron-lock-5
report_interval_s = 300
level_alarm_cm_per_h = 10
```

## Training

New lock keepers shadow an experienced keeper for ten shifts before working alone.
"""


# ---------- TXT: Mont Rivière (Latin-1, ALL-CAPS headings, schedule and checklist far apart) ----------

MONT_RIVIERE = """\
MONT RIVIÈRE UPPER-AIR STATION

The Mont Rivière station sits at 1,840 m above the village of Saint-Clément-sur-Arve. It launches
radiosonde balloons and reports to the regional forecasting centre in Annecy.

DAILY OBSERVATION SCHEDULE

Surface observations are taken every hour from 05:00 to 21:00.
Radiosonde balloons are launched at 06:00 and 18:00 local time.
The data summary is sent to Annecy at 07:30 and 19:30.

STAFF

The station chief is Hélène Côté. Observers are Gérard Lefèvre and Zoë Bréhaut.
One observer is on duty at all times; the chief covers weekends in rotation.

ROAD ACCESS

The station is reached by the Combe-à-l'Âne forest road, which is closed to private cars.
In snow, use the tracked vehicle kept in the lower garage.

WINTER OPERATIONS

From December to March the access road is ploughed by the commune at 06:00.
Spare batteries for the anemometer are kept in the heated store.

OPENING CHECKLIST

1. Read the barometer and log the pressure.
2. Check the hydrogen-free status of the launch shed.
3. Inspect the radiosonde battery and the ground receiver.
4. Confirm the satellite link to Annecy.

DATA TRANSMISSION

Messages are sent in the WMO TEMP format. If the satellite link fails, use the backup telephone line.

LIGHTNING PROTOCOL

If lightning is detected within 15 km, suspend balloon launches, disconnect the antenna mast,
and keep all staff inside until 30 minutes after the last strike.

HELIUM RESERVE

The helium reserve is read every Monday. Do not reorder helium while the reserve is 128 cubic
metres or more; below 128 cubic metres, place an order with the supplier in Grenoble.

VISITORS

School groups may visit on Wednesdays by appointment. Visitors must not enter the launch shed.
"""


# ---------- CSV: Tidal Grid (typed codes, dates, quoted commas) ----------

TIDAL_GRID = [
    ["asset_id", "category", "zone", "units", "last_inspection", "status", "action_code", "notes"],
    ["TG-101", "Buoy", "North", "48", "2026-03-02", "Ready", "A1", "Repainted"],
    ["TG-102", "Buoy", "North", "52", "2026-01-15", "Overdue", "C3", "Light flickers, check battery"],
    ["TG-201", "Sensor", "East", "30", "2026-05-20", "Ready", "A1", ""],
    ["TG-202", "Sensor", "East", "36", "2025-11-30", "Overdue", "C3", "Cable chafed, replace by spring"],
    ["TG-203", "Sensor", "East", "28", "2026-06-11", "Ready", "B2", "Firmware 4.2"],
    ["TG-301", "Turbine", "South", "90", "2026-02-27", "Overdue", "D4", "Blade pitch fault, crane needed"],
    ["TG-302", "Turbine", "South", "84", "2026-04-08", "Ready", "A1", ""],
    ["TG-401", "Cable", "West", "40", "2026-07-01", "Ready", "B2", "Spliced, monitored"],
    ["TG-402", "Cable", "West", "32", "2025-12-19", "Overdue", "C3", "Insulation test failed"],
    ["TG-403", "Cable", "West", "24", "2026-08-15", "Maintenance", "B2", "Joint box, East side"],
]


# ---------- HTML: a standards page with RFC 2119 keywords (written for this test, not a real RFC) ----------

HARBOUR_NAMES = """\
<!doctype html>
<html><head><title>HT-NAMES: Reserved Names for Harbour Telemetry</title>
<meta name="author" content="Harbour Telemetry Working Group"></head>
<body><nav><a href="/">Home</a> | <a href="/profiles">Profiles</a></nav>
<main><article>
<h1>HT-NAMES: Reserved Names for Harbour Telemetry</h1>
<p>Published 2026-05-04 by the Harbour Telemetry Working Group.</p>
<h2>1. Requirements language</h2>
<p>The key words "MUST", "MUST NOT", "REQUIRED", "SHOULD", "SHOULD NOT" and "MAY" in this
profile are to be interpreted as described in RFC 2119.</p>
<h2>2. Purpose</h2>
<p>Telemetry devices on a harbour network need device names that can never collide with real
names. This profile reserves two name suffixes, .quayside and .sample, and says how software
treats each one.</p>
<h2>3. The .quayside suffix</h2>
<p>Names ending in .quayside always refer to a device on the local harbour segment.</p>
<p>Applications SHOULD recognise .quayside names and SHOULD resolve them to the local segment
without asking a public name server. Name resolution libraries MUST NOT forward .quayside
queries to the public DNS. Gateways MAY cache .quayside answers for up to 60 seconds.</p>
<h2>4. The .sample suffix</h2>
<p>Names ending in .sample are for documentation and examples only.</p>
<p>Authors MAY use .sample names freely in manuals. Applications SHOULD NOT treat .sample names
specially. Name servers SHOULD NOT answer queries for .sample names with real addresses.</p>
<h2>5. Logging</h2>
<p>Devices MUST log every name lookup that fails. Logs SHOULD be kept for 30 days.</p>
<h2>6. Security considerations</h2>
<p>Because .quayside names are local, an attacker on the segment can impersonate a device.
Operators SHOULD use authenticated telemetry where possible.</p>
<h2>7. Registry</h2>
<p>The working group keeps the list of reserved suffixes. New suffixes REQUIRE a published profile.</p>
</article></main>
<footer>Harbour Telemetry Working Group</footer></body></html>
"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    make_pdf()
    make_docx()
    (OUT / "ember_canal.md").write_text(EMBER_CANAL, encoding="utf-8")
    (OUT / "mont_riviere.txt").write_bytes(MONT_RIVIERE.encode("latin-1"))
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(TIDAL_GRID)
    (OUT / "tidal_grid.csv").write_text(buffer.getvalue(), encoding="utf-8")
    # The headerless copy must be rejected at upload.
    (OUT / "tidal_grid_headerless.csv").write_text(buffer.getvalue().split("\n", 1)[1], encoding="utf-8")
    (OUT / "harbour_names.html").write_text(HARBOUR_NAMES, encoding="utf-8")
    for path in sorted(OUT.iterdir()):
        print(f"{path.stat().st_size:7} bytes  {path.name}")


if __name__ == "__main__":
    main()
