"""Render technical_report.md to a print-ready PDF with headless Chrome."""
import pathlib
import subprocess
import sys

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
md = (ROOT / "technical_report.md").read_text()
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
css = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font: 9.6pt/1.42 "Inter", -apple-system, "Helvetica Neue", Arial, sans-serif; color: #17150F; }
h1 { font-size: 20pt; letter-spacing: -0.02em; margin: 0 0 6pt; }
h2 { font-size: 12.5pt; margin: 13pt 0 4pt; color: #17150F; border-bottom: 1px solid #EBE3D7; padding-bottom: 2pt; }
h3 { font-size: 10.5pt; margin: 9pt 0 3pt; }
p, li { margin: 3pt 0; }
ul { padding-left: 14pt; margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 7pt; font-size: 8.6pt; }
th, td { border-bottom: 1px solid #EBE3D7; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #F3ECE1; }
code { font: 8.4pt "JetBrains Mono", Menlo, monospace; background: #F3ECE1; padding: 0 2pt; border-radius: 2pt; }
pre { background: #FAF6EF; border: 1px solid #EBE3D7; padding: 5pt 7pt; border-radius: 4pt; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
blockquote { margin: 4pt 0; padding-left: 8pt; border-left: 3px solid #D66B38; color: #423C33; }
img { max-width: 100%; }
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
out_html = ROOT / "docs" / "report.html"
out_html.write_text(html)
pdf = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "DhirajKavuri_Report.pdf")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", out_html.as_uri()], check=True, capture_output=True)
print("wrote", pdf)
