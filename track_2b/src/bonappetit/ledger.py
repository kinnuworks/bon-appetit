"""Add up linked lines into a household picture. Code does all of the arithmetic."""
from __future__ import annotations

import re

from .catalog import Catalog
from .foodlayer import DAILY_REFERENCE_G, GROUPS
from .llm import Apertus

DEFAULT_PACK_G = {  # used only when a line carries no pack size; flagged as estimated
    "vegetables_fruit": 500, "grains_potatoes": 500, "dairy": 500, "protein": 300,
    "fats_nuts": 200, "sweets_snacks_drinks": 250, "drinks_unsweetened": 1000, "mixed": 400,
}


def grams_for(link: dict, catalog: Catalog) -> tuple[float, bool]:
    line, choice = link["line"], link["choice"]
    est = line.get("pack_grams") is None
    grams = line.get("pack_grams") or DEFAULT_PACK_G.get(choice["group"], 400)
    if line.get("pack_is_volume"):
        dens = catalog.row(choice["fsvo_id"]).get("density")
        grams *= float(dens) if dens == dens and dens else 1.0
    return grams * (line.get("qty") or 1), est


def summarise(links: list[dict], catalog: Catalog, *, adults: float = 1.0, days: float = 7.0) -> dict:
    by_group = {g: 0.0 for g in GROUPS}
    totals = {"sugars": 0.0, "salt": 0.0, "saturated_fat": 0.0, "energy_kcal": 0.0}
    estimated = 0
    for l in links:
        if l["status"] not in ("linked", "vetoed") or not l.get("choice"):
            continue
        grams, est = grams_for(l, catalog)
        estimated += est
        by_group[l["choice"]["group"]] += grams
        n = catalog.nutrients(l["choice"]["fsvo_id"])
        for k in totals:
            totals[k] += (n.get(k) or 0) * grams / 100
    per_day = {g: v / (adults * days) for g, v in by_group.items()}
    return {
        "grams_per_adult_day": {g: round(v) for g, v in per_day.items()},
        "reference_per_adult_day": DAILY_REFERENCE_G,
        "ratio_to_reference": {g: round(per_day[g] / ref, 2) for g, ref in DAILY_REFERENCE_G.items()},
        "per_adult_day": {k: round(v / (adults * days), 1) for k, v in totals.items()},
        "lines_total": len(links),
        "lines_linked": sum(l["status"] in ("linked", "vetoed") for l in links),
        "lines_review": sum(l["status"] == "review" for l in links),
        "lines_nonfood": sum(l["status"] == "nonfood" for l in links),
        "pack_size_estimated": estimated,
    }


NUDGE_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}
LANG_NAMES = {"de": "German (Swiss spelling, ss instead of ß)", "fr": "French", "it": "Italian", "en": "English"}


GROUP_NAMES = {
    "de": {"vegetables_fruit": "Gemüse und Früchte", "dairy": "Milchprodukte", "grains_potatoes": "Getreide und Kartoffeln",
           "sweets_snacks_drinks": "Süsses, Snacks und Süssgetränke", "protein": "Fleisch, Fisch, Eier", "fats_nuts": "Öle, Fette und Nüsse"},
    "fr": {"vegetables_fruit": "légumes et fruits", "dairy": "produits laitiers", "grains_potatoes": "céréales et pommes de terre",
           "sweets_snacks_drinks": "sucreries, snacks et boissons sucrées", "protein": "viande, poisson, œufs", "fats_nuts": "huiles, graisses et noix"},
    "it": {"vegetables_fruit": "verdura e frutta", "dairy": "latticini", "grains_potatoes": "cereali e patate",
           "sweets_snacks_drinks": "dolci, snack e bibite zuccherate", "protein": "carne, pesce, uova", "fats_nuts": "oli, grassi e noci"},
    "en": {"vegetables_fruit": "vegetables and fruit", "dairy": "dairy", "grains_potatoes": "grains and potatoes",
           "sweets_snacks_drinks": "sweets, snacks and sweet drinks", "protein": "meat, fish and eggs", "fats_nuts": "oils, fats and nuts"},
}


def nudge(summary: dict, llm: Apertus, lang: str = "en") -> str:
    """One friendly suggestion. Numbers reach the text only through slots that code fills."""
    ratio = summary["ratio_to_reference"]
    low = min(("vegetables_fruit", "dairy", "grains_potatoes"), key=lambda g: ratio[g])
    high = max(("sweets_snacks_drinks", "protein", "fats_nuts"), key=lambda g: ratio[g])
    slots = {
        "{LOW_PCT}": f"{round(ratio[low] * 100)}%",
        "{HIGH_PCT}": f"{round(ratio[high] * 100)}%",
        "{SUGAR_G}": f"{summary['per_adult_day']['sugars']:.0f} g",
    }
    names = GROUP_NAMES[lang]
    if ratio[high] > 1:
        facts = (f"they buy too little '{names[low]}' ({{LOW_PCT}} of the guide) and too much '{names[high]}' "
                 f"({{HIGH_PCT}} of the guide). Suggest one concrete swap at the supermarket that moves from the second "
                 "group to the first.")
    else:
        facts = (f"they buy too little '{names[low]}' ({{LOW_PCT}} of the guide). Suggest one concrete thing to add or "
                 "swap at the supermarket.")
    msg = (
        f"Write two short, friendly sentences in {LANG_NAMES[lang]} for a household. Facts: {facts} Write the "
        "placeholders exactly as given and no other numbers. No praise, no medical advice. "
        "Reply in JSON with one key, text."
    )
    text = llm.json([{"role": "user", "content": msg}], NUDGE_SCHEMA, max_tokens=160).get("text", "")
    text = re.sub(r"\d+(?:[.,]\d+)?\s*(?:%|g\b)", "", text) if not any(s in text for s in slots) else text
    for k, v in slots.items():
        text = text.replace(k, v)
    text = re.sub(r"\s+[–—]\s+", ", ", text)
    if lang == "de":  # Swiss spelling: the 8B model writes ß even when asked not to
        text = text.replace("ß", "ss")
    return text.strip()
