"""Turn the vector PDFs from make_pdfs.py into SVG files for the site (text drawn as outlines). Needs PyMuPDF."""
import pathlib
import re

import pymupdf as fitz  # PyMuPDF

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "build" / "pdf", ROOT / "public" / "assets" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
#: Settings is shown without its left-hand list of pages, so the page itself is large enough to read.
CROPS = {"settings-learned": (196, 0, 764, 1010)}
for pdf in sorted(SRC.glob("*.pdf")):
    page = fitz.open(pdf)[0]
    svg = page.get_svg_image(text_as_path=True)
    svg = re.sub(r'\swidth="[\d.]+"\s+height="[\d.]+"', "", svg, count=1)         # let the page decide the size (viewBox keeps the shape)
    crop = CROPS.get(pdf.stem)                                                       # (x, y, width, height) of the part to show
    if crop:
        svg = re.sub(r'viewBox="[^"]*"', 'viewBox="%s %s %s %s"' % crop, svg, count=1)
    (OUT / f"{pdf.stem}.svg").write_text(svg, encoding="utf-8")
    print(pdf.stem, f"{len(svg) // 1024} KB", page.rect)
