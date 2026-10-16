"""Turn receipts into lines. Everything here is deterministic; no model is involved.

Supported inputs: a Migros Cumulus CSV export, the text of a Coop PDF receipt, or plain
pasted text with one article per line. Prices, quantities, pack sizes and multipacks are
read by rules so that the language model never has to produce a number.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass, field

NON_FOOD_HINTS = (
    "TRAGTASCHE", "SACK", "SAC ", "BORSA", "DEPOT", "CONSIGNE", "PFAND", "RABATT", "AKTION",
    "CUMULUS", "SUPERCARD", "TOTAL", "BAR ", "TWINT", "KARTE", "MWST", "TVA", "IVA", "RUNDUNG",
    "GUTSCHEIN", "BON ", "WASCHMITTEL", "LESSIVE", "DETERSIVO", "TOILETTENPAPIER", "HAUSHALT",
    "BATTERIE", "ZAHNPASTA", "SHAMPOO", "DUSCHGEL",
)

# 6X1.5L, 4x125G, 2 X 500 G, 500G, 1L, 75CL, 1,5L, 250ML, 1KG
_PACK = re.compile(
    r"(?:(?P<n>\d{1,2})\s*[xX×]\s*)?(?P<amt>\d+(?:[.,]\d+)?)\s*(?P<unit>KG|G|GR|L|LT|CL|DL|ML)\b",
    re.IGNORECASE,
)
_PRICE = re.compile(r"(-?\d+[.,]\d{2})\s*[A-Z]?\s*$")
_QTY_PREFIX = re.compile(r"^\s*(?P<q>\d{1,2})\s*[xX×*]\s+")

_UNIT_TO_G = {"kg": 1000, "g": 1, "gr": 1, "l": 1000, "lt": 1000, "cl": 10, "dl": 100, "ml": 1}


@dataclass
class Line:
    raw: str
    text: str
    qty: float = 1.0
    price: float | None = None
    pack_grams: float | None = None  # grams or millilitres for one unit as sold
    pack_is_volume: bool = False
    nonfood_hint: bool = False
    shop: str | None = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def parse_pack(text: str) -> tuple[float | None, bool]:
    """Return (grams or ml per unit, is_volume) from strings like '6X1.5L' or '200G'."""
    m = None
    for m in _PACK.finditer(text):
        pass  # the last size mentioned on a line is the pack size
    if not m:
        return None, False
    n = int(m.group("n")) if m.group("n") else 1
    amt = float(m.group("amt").replace(",", "."))
    unit = m.group("unit").lower()
    return n * amt * _UNIT_TO_G[unit], unit in {"l", "lt", "cl", "dl", "ml"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_line(raw: str, *, qty: float = 1.0, price: float | None = None, shop: str | None = None) -> Line:
    text = _clean(raw)
    m = _QTY_PREFIX.match(text)
    if m:
        qty = float(m.group("q"))
        text = text[m.end():]
    if price is None:
        pm = _PRICE.search(text)
        if pm:
            price = float(pm.group(1).replace(",", "."))
            text = _clean(text[: pm.start()])
    grams, is_vol = parse_pack(text)
    upper = f" {text.upper()} "
    hint = any(h in upper for h in NON_FOOD_HINTS) or (price is not None and price < 0)
    return Line(raw=raw.strip(), text=text, qty=qty, price=price, pack_grams=grams,
                pack_is_volume=is_vol, nonfood_hint=hint, shop=shop)


def parse_text(text: str, shop: str | None = None) -> list[Line]:
    out = []
    for raw in text.splitlines():
        if len(raw.strip()) < 3 or not re.search(r"[A-Za-zÀ-ÿ]{2}", raw):
            continue
        out.append(make_line(raw, shop=shop))
    return out


def parse_migros_csv(data: str) -> list[Line]:
    """Migros Cumulus 'Meine Kassenbons' CSV export (semicolon separated).

    Column names vary between export versions, so we look them up loosely.
    """
    sample = data[:2048]
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    rows = list(csv.DictReader(io.StringIO(data), dialect=dialect))
    if not rows:
        return []
    keys = {k.lower(): k for k in rows[0].keys() if k}

    def col(*names):
        for n in names:
            for k_low, k in keys.items():
                if n in k_low:
                    return k
        return None

    c_name = col("artikel", "article", "produkt", "bezeichnung", "description")
    c_qty = col("menge", "anzahl", "quantit")
    c_price = col("umsatz", "betrag", "preis", "prix", "amount", "total")
    lines = []
    for r in rows:
        name = (r.get(c_name) or "").strip() if c_name else ""
        if not name:
            continue
        qty = _num(r.get(c_qty)) if c_qty else 1.0
        price = _num(r.get(c_price)) if c_price else None
        lines.append(make_line(name, qty=qty or 1.0, price=price, shop="Migros"))
    return lines


def parse_pdf(path: str, shop: str | None = "Coop") -> list[Line]:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return parse_text(text, shop=shop)


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace("'", "").replace(",", ".").strip())
    except ValueError:
        return None
