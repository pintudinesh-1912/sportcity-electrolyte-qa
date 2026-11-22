"""Render findings-report.md -> findings-report.html -> findings-report.pdf (via headless Chrome).

    uv run --with markdown python part2-findings/build_report.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).parent
SRC = HERE / "findings-report.md"
HTML = HERE / "findings-report.html"
PDF = HERE / "findings-report.pdf"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CSS = """
@page { size: A4; margin: 13mm 13mm 12mm; }
* { box-sizing: border-box; }
body { font: 9.4pt/1.38 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: #1c2321; margin: 0; }
h1 { font-size: 15pt; margin: 0 0 3pt; color: #0b4f45; }
h2 { font-size: 11pt; margin: 9pt 0 3pt; color: #0b4f45; border-bottom: 1px solid #cfdcd8; padding-bottom: 1pt; }
p { margin: 3pt 0; }
ul, ol { margin: 3pt 0; padding-left: 15pt; }
li { margin: 1.5pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; font-size: 8.4pt; }
th, td { border: 1px solid #d5dfdc; padding: 2.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #eaf2f0; }
tr { break-inside: avoid; }
td:first-child { white-space: nowrap; }
code { font: 8pt ui-monospace, Menlo, monospace; background: #f1f4f3; padding: 0 2px; border-radius: 2px; }
.page-break { break-after: page; }
.shots { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; }
figure { margin: 0; break-inside: avoid; }
figure img { width: 100%; border: 1px solid #d5dfdc; }
figure.narrow img { width: 60%; }
figcaption { font-size: 8pt; color: #4d5b57; }
"""


def main() -> int:
    body = markdown.markdown(SRC.read_text(encoding="utf-8"), extensions=["tables", "sane_lists"])
    HTML.write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>Electrolyte QA findings</title>'
        f"<style>{CSS}</style></head><body>{body}</body></html>",
        encoding="utf-8",
    )
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={PDF}", HTML.resolve().as_uri()],
        check=True, capture_output=True,
    )
    print(f"Wrote {HTML.name} and {PDF.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
