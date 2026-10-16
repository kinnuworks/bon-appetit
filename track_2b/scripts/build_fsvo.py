"""Turn the FSVO Swiss Food Composition Database (V6.5) into one tidy CSV.

Source: naehrwertdaten.ch, Federal Food Safety and Veterinary Office (FSVO).
Free to reuse with attribution.
"""
import re
import sys
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/raw/fsvo.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/fsvo.csv"

WANTED = {
    "Energie, Kalorien (kcal)": "energy_kcal",
    "Fett, total (g)": "fat",
    "Fettsäuren, gesättigt (g)": "saturated_fat",
    "Kohlenhydrate, verfügbar (g)": "carbohydrates",
    "Zucker (g)": "sugars",
    "Nahrungsfasern (g)": "fiber",
    "Protein (g)": "proteins",
    "Salz (NaCl) (g)": "salt",
}


def load(sheet, kind):
    raw = pd.read_excel(SRC, sheet_name=sheet, header=2)
    keep = {"ID": "fsvo_id", "Name": "name", "Synonyme": "synonyms", "Kategorie": "category",
            "Dichte": "density", "Bezugseinheit": "basis"}
    df = raw[list(keep)].rename(columns=keep)
    for col, short in WANTED.items():
        match = [c for c in raw.columns if c.strip() == col]
        if not match:
            raise SystemExit(f"missing column {col!r} in {sheet}")
        df[short] = pd.to_numeric(raw[match[0]].astype(str).str.replace("<", "").str.replace("tr.", "0", regex=False), errors="coerce")
    df["kind"] = kind
    return df


df = pd.concat([load("Generische Lebensmittel", "generic"), load("Markenprodukte", "brand")], ignore_index=True)
df = df.dropna(subset=["fsvo_id", "name"])
df["fsvo_id"] = df["fsvo_id"].astype(int)
df["liquid"] = df["basis"].astype(str).str.contains("ml")
df["category_top"] = df["category"].astype(str).str.split("/").str[0]
df.to_csv(OUT, index=False)
print(len(df), "foods;", df["kind"].value_counts().to_dict())
print(df["category_top"].value_counts().head(20).to_string())
