"""Build the evaluation set: real Swiss products with printed nutrition values.

Source: Open Food Facts (ODbL). Each item keeps its barcode, so anyone can check it.
For every product we make a receipt-style line with documented, deterministic rules,
because no licensed corpus of real Swiss receipt lines exists.
"""
from __future__ import annotations

import html
import json
import re
import sys
import unicodedata

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/off_ch.parquet"
OUT = sys.argv[2] if len(sys.argv) > 2 else "eval/gold.jsonl"
N = {"de": 80, "fr": 50, "it": 30}
SEED = 42

# Shop-brand shorthand as it appears on Swiss receipts (documented in docs/receipt_rules.md).
BRAND_SHORT = [
    (r"\bm-budget\b", "M-BUDG"), (r"\bm-classic\b", "M-CL"), (r"\bprix garantie\b", "PRIX GAR."),
    (r"\bqualit[ée] ?& ?prix\b", "QP"), (r"\bnaturaplan\b", "NATURAPL."), (r"\bbetty bossi\b", "B.BOSSI"),
    (r"\banna'?s best\b", "ANNAS B."), (r"\bs[ée]lection\b", "SEL."), (r"\bbio\b", "BIO"),
]


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def receipt_line(name: str, brand: str, qty: str) -> str:
    s = f"{brand.split(',')[0]} {name}" if brand and brand.split(",")[0].lower() not in name.lower() else name
    s = s.lower()
    for pat, rep in BRAND_SHORT:
        s = re.sub(pat, rep.lower(), s)
    s = fold(s).upper()
    s = re.sub(r"[^A-Z0-9 .&'-]", " ", s)
    words = []
    for w in s.split():
        # long words are cut to 7 letters plus a dot, as till systems do
        words.append(w[:7] + "." if len(w) > 9 and w.isalpha() else w)
    s = " ".join(words)[:24].rstrip(" .")
    q = re.sub(r"\s+", "", (qty or "").upper())
    if re.fullmatch(r"\d+(?:[.,]\d+)?(?:G|KG|ML|CL|L)", q):
        s = f"{s} {q}"
    return s


def name_in(names, lang):
    for n in names if names is not None else []:
        if n["lang"] == lang and n["text"]:
            return html.unescape(n["text"]).strip()
    return None


def main():
    df = pd.read_parquet(SRC)
    need = ["energy_kcal", "fat", "carbohydrates", "sugars", "proteins", "salt"]
    df = df.dropna(subset=need)
    df = df[(df.energy_kcal > 0) & (df.energy_kcal < 900) & (df.salt < 30)]
    rows = []
    for lang, n in N.items():
        sub = df.copy()
        sub["name"] = sub["product_name"].map(lambda v: name_in(v, lang))
        sub = sub[sub["name"].str.len().between(4, 60, inclusive="both").fillna(False)]
        sub = sub[sub["lang"] == lang]
        sub = sub.drop_duplicates("name").sample(n=min(n, len(sub)), random_state=SEED)
        for r in sub.itertuples():
            brand = html.unescape(r.brands) if isinstance(r.brands, str) else ""
            qty = r.quantity if isinstance(r.quantity, str) else ""
            rows.append({
                "barcode": r.code, "lang": lang, "name": r.name, "brand": brand,
                "quantity": qty, "receipt_line": receipt_line(r.name, brand, qty),
                "label": {k: float(getattr(r, k)) for k in need},
                "food_groups": list(r.food_groups_tags) if r.food_groups_tags is not None else [],
                "nova": None if pd.isna(r.nova_group) else int(r.nova_group),
                "licence": "ODbL-1.0 (Open Food Facts)",
            })
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "items", pd.Series([r["lang"] for r in rows]).value_counts().to_dict(), "of", len(df), "eligible")


if __name__ == "__main__":
    main()
