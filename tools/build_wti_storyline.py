"""Build the April 2020 WTI Storyline visual from pinned series and cards.

Stdlib only. The HTML is a self-contained annotated line chart that follows
the Knight Lab StorylineJS data contract (CSV + <=12 cards) without Google
Sheets. ``--check`` rebuilds and compares to the committed file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "docs" / "storyline" / "public_wti_april_2020"
SERIES_PATH = CASE_DIR / "series.csv"
CARDS_PATH = CASE_DIR / "storyline.json"
PROVENANCE_PATH = CASE_DIR / "provenance.json"
HTML_PATH = CASE_DIR / "index.html"
MAX_CARDS = 12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_series(path: Path = SERIES_PATH) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                (datetime.strptime(raw["date"], "%Y-%m-%d").date(), float(raw["wti_usd_per_bbl"]))
            )
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expand_weeks(payload: dict[str, Any]) -> list[tuple[date, float]]:
    from datetime import timedelta

    points: list[tuple[date, float]] = []
    window = payload["window"]
    start_bound = datetime.strptime(window["start"], "%Y-%m-%d").date()
    end_bound = datetime.strptime(window["end"], "%Y-%m-%d").date()
    for week in payload["weeks"]:
        week_start = datetime.strptime(week["week_start"], "%Y-%m-%d").date()
        for offset, value in enumerate(week["values"]):
            if value is None:
                continue
            day = week_start + timedelta(days=offset)
            if start_bound <= day <= end_bound:
                points.append((day, float(f"{float(value):.2f}")))
    return points


def _scale(value: float, lo: float, hi: float, start: float, end: float) -> float:
    if hi == lo:
        return (start + end) / 2
    t = (value - lo) / (hi - lo)
    return start + t * (end - start)


def _polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def render_html(
    series: list[tuple[date, float]],
    config: dict[str, Any],
    provenance: dict[str, Any],
) -> str:
    width, height = 960, 420
    left, right, top, bottom = 64, 24, 28, 48
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_min, y_max = -45.0, 70.0
    x_lo = series[0][0].toordinal()
    x_hi = series[-1][0].toordinal()

    def xy(day: date, value: float) -> tuple[float, float]:
        x = _scale(day.toordinal(), x_lo, x_hi, left, left + plot_w)
        y = _scale(value, y_min, y_max, top + plot_h, top)
        return x, y

    line = _polyline([xy(day, value) for day, value in series])
    zero_y = xy(series[0][0], 0.0)[1]

    y_ticks = [60, 40, 20, 0, -20, -40]
    y_grid = []
    for tick in y_ticks:
        y = xy(series[0][0], float(tick))[1]
        y_grid.append(
            f'<line x1="{left}" x2="{left + plot_w}" y1="{y:.2f}" y2="{y:.2f}" />'
            f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end">{tick}</text>'
        )

    month_starts = []
    seen_months: set[tuple[int, int]] = set()
    for day, _value in series:
        key = (day.year, day.month)
        if key in seen_months:
            continue
        seen_months.add(key)
        month_starts.append(day)
    x_labels = []
    for day in month_starts:
        x = xy(day, 0.0)[0]
        x_labels.append(
            f'<text x="{x:.2f}" y="{height - 16}" text-anchor="middle">{day.strftime("%b")}</text>'
        )

    cards = config["cards"]
    markers = []
    card_items = []
    for index, card in enumerate(cards):
        day, value = series[card["row_number"]]
        x, y = xy(day, value)
        markers.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" />'
            f'<text x="{x:.2f}" y="{y - 12:.2f}" text-anchor="middle">{index + 1}</text>'
        )
        card_items.append(
            "<li>"
            f"<span class='n'>{index + 1}</span>"
            f"<time datetime='{day.isoformat()}'>{escape(card['display_date'])}</time>"
            f"<h2>{escape(card['title'])}</h2>"
            f"<p>{escape(card['text'])}</p>"
            f"<p class='meta'>spot {value:+.2f} USD/bbl</p>"
            "</li>"
        )

    bindings = provenance["cell_bindings"]
    linked = provenance["linked_public_case"]
    rows = []
    for item in bindings:
        rows.append(
            "<tr>"
            f"<td>{escape(item['sheet'])}!{escape(item['cell'])}</td>"
            f"<td>{item['value']}</td>"
            f"<td>{escape(item['claim'])}</td>"
            f"<td><a href='{escape(item['source_url'])}'>{escape(item['source_url'])}</a></td>"
            "</tr>"
        )

    svg = f"""<svg viewBox="0 0 {width} {height}" role="img" aria-label="EIA Cushing WTI spot, January to July 2020">
  <rect class="bg" x="0" y="0" width="{width}" height="{height}" />
  <g class="grid">{''.join(y_grid)}</g>
  <line class="zero" x1="{left}" x2="{left + plot_w}" y1="{zero_y:.2f}" y2="{zero_y:.2f}" />
  <polyline class="series" fill="none" points="{line}" />
  <g class="markers">{''.join(markers)}</g>
  <g class="xlabels">{''.join(x_labels)}</g>
  <text class="ylabel" x="18" y="{top + plot_h / 2}" transform="rotate(-90 18,{top + plot_h / 2})" text-anchor="middle">USD per barrel (Cushing spot)</text>
</svg>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>April 2020 WTI — hashed public case</title>
  <style>
    :root {{ --ink:#1a1a1a; --muted:#5c5c5c; --paper:#f7f4ee; --line:#1f4e78; --rule:#d9d1c3; }}
    body {{ margin:0 auto; max-width:960px; padding:28px 20px 64px; font:18px/1.45 Georgia, "Times New Roman", serif; background:var(--paper); color:var(--ink); }}
    .kicker {{ text-transform:uppercase; letter-spacing:.08em; font:12px/1.2 ui-sans-serif, system-ui, sans-serif; color:var(--muted); margin:0 0 8px; }}
    h1 {{ font-size:32px; line-height:1.2; margin:0 0 12px; font-weight:normal; }}
    .dek {{ color:var(--muted); margin:0 0 24px; }}
    figure {{ margin:0 0 28px; }}
    svg {{ width:100%; height:auto; background:#fff; border:1px solid var(--rule); }}
    svg .bg {{ fill:#fff; }}
    svg .grid line {{ stroke:var(--rule); stroke-width:1; }}
    svg .grid text, svg .xlabels text, svg .ylabel, svg .markers text {{ font:11px/1 ui-sans-serif, system-ui, sans-serif; fill:var(--muted); }}
    svg .zero {{ stroke:#9b1c1c; stroke-dasharray:4 4; }}
    svg .series {{ stroke:var(--line); stroke-width:2; }}
    svg .markers circle {{ fill:var(--line); stroke:#fff; stroke-width:2; }}
    ol.cards {{ list-style:none; padding:0; margin:0 0 32px; display:grid; gap:16px; }}
    ol.cards li {{ background:#fff; border:1px solid var(--rule); padding:16px 16px 16px 48px; position:relative; }}
    ol.cards .n {{ position:absolute; left:14px; top:16px; font:700 14px/1 ui-sans-serif, system-ui, sans-serif; color:var(--line); }}
    ol.cards time {{ font:12px/1.2 ui-sans-serif, system-ui, sans-serif; color:var(--muted); }}
    ol.cards h2 {{ font-size:20px; margin:4px 0 8px; font-weight:normal; }}
    ol.cards p {{ margin:0 0 8px; }}
    ol.cards .meta {{ font:12px/1.2 ui-sans-serif, system-ui, sans-serif; color:var(--muted); margin:0; }}
    table {{ width:100%; border-collapse:collapse; font:14px/1.4 ui-sans-serif, system-ui, sans-serif; background:#fff; }}
    th, td {{ text-align:left; padding:8px; border-bottom:1px solid var(--rule); vertical-align:top; }}
    th {{ font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
    footer {{ margin-top:28px; font-size:14px; color:var(--muted); }}
    a {{ color:var(--line); }}
    code {{ font:13px/1.4 ui-monospace, monospace; }}
  </style>
</head>
<body>
  <p class="kicker">Finance-Segway public case · Storyline visual · not a trading signal</p>
  <h1>Oil settled below zero. Every plotted point and every model cell has a source.</h1>
  <p class="dek">Line: EIA Cushing WTI <em>spot</em> (RWTC), pinned 2026-08-20.
  Cards cite the hashed April 2020 public-case cells. Spot on 20 Apr 2020 is
  <strong>-36.98</strong>; hashed <code>Hedging!C7</code> is the May futures
  settlement <strong>-37.63</strong>. Matching bytes are not a correct model.</p>
  <figure>{svg}</figure>
  <ol class="cards">{''.join(card_items)}</ol>
  <h2>Hashed model cells</h2>
  <p>Workbook SHA-256 <code>{escape(linked['workbook_sha256'])}</code></p>
  <table>
    <thead><tr><th>Cell</th><th>Value</th><th>Claim</th><th>Source</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <footer>
    <p>Classification: <code>{escape(provenance['classification'])}</code>.
    Counts toward M4: {str(provenance['counts_toward_M4']).lower()}.
    Case <code>{escape(linked['case_id'])}</code>.
    Rebuild: <code>python3 tools/build_wti_storyline.py --check</code>.</p>
    <p>Educational historical reconstruction only. Not financial, legal, tax,
    accounting, actuarial, or investment advice. Not a Bloomberg terminal.</p>
  </footer>
</body>
</html>
"""


def build() -> str:
    series = load_series()
    config = load_json(CARDS_PATH)
    provenance = load_json(PROVENANCE_PATH)
    html = render_html(series, config, provenance)
    HTML_PATH.write_text(html, encoding="utf-8")
    return html


def check() -> None:
    provenance = load_json(PROVENANCE_PATH)
    expected = {
        SERIES_PATH: provenance["series"]["sha256"],
        CASE_DIR / "source_weeks.json": provenance["series"]["source_weeks_sha256"],
        CARDS_PATH: provenance["storyline"]["sha256"],
    }
    for path, digest in expected.items():
        actual = sha256(path)
        if actual != digest:
            raise SystemExit(f"{path.relative_to(ROOT)} sha256 mismatch")
    committed = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    series = load_series()
    config = load_json(CARDS_PATH)
    rendered = render_html(series, config, provenance)
    if rendered != committed:
        raise SystemExit("index.html is stale; run tools/build_wti_storyline.py")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
        print("ok")
        return
    build()
    print(HTML_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
