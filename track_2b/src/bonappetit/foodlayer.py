"""The symbolic food layer: groups, reference amounts and the checks that veto a link.

Food groups follow the Swiss food pyramid of the Swiss Society for Nutrition (SGE).
Daily reference amounts per adult are derived from the SGE portion recommendations
(see docs/food_layer.md for the derivation). They are guidance for a household
picture, not a clinical target.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

GROUPS = {
    "vegetables_fruit": "Vegetables and fruit",
    "grains_potatoes": "Grains, potatoes and legumes",
    "dairy": "Milk and dairy",
    "protein": "Meat, fish, eggs and alternatives",
    "fats_nuts": "Oils, fats and nuts",
    "sweets_snacks_drinks": "Sweets, salty snacks and sweet or alcoholic drinks",
    "drinks_unsweetened": "Water, tea and coffee",
    "mixed": "Ready meals and mixed dishes",
}

# grams per adult per day, from SGE portions:
# 5 x 120 g vegetables and fruit; 3 x (75-125 g bread, or 180-300 g potatoes, or 60-100 g pasta/rice dry);
# 3 x dairy (200 ml milk, 150-200 g yoghurt, 30 g hard cheese); 1 x 100-120 g meat/fish/eggs/tofu;
# 2-3 tbsp oil plus 20-30 g nuts; sweets and snacks at most one small portion.
DAILY_REFERENCE_G = {
    "vegetables_fruit": 600,
    "grains_potatoes": 330,
    "dairy": 450,
    "protein": 110,
    "fats_nuts": 55,
    "sweets_snacks_drinks": 50,
}

CATEGORY_TO_GROUP = {
    "Gemüse": "vegetables_fruit",
    "Früchte": "vegetables_fruit",
    "Getreideprodukte, Hülsenfrüchte und Kartoffeln": "grains_potatoes",
    "Brote, Flocken und Frühstückscerealien": "grains_potatoes",
    "Milch und Milchprodukte": "dairy",
    "Fleisch und Innereien": "protein",
    "Fleisch- und Wurstwaren": "protein",
    "Fisch": "protein",
    "Eier": "protein",
    "Fleischersatzprodukte": "protein",
    "Fette und Öle": "fats_nuts",
    "Nüsse, Samen und Ölfrüchte": "fats_nuts",
    "Süssigkeiten": "sweets_snacks_drinks",
    "Salzige Snacks": "sweets_snacks_drinks",
    "Alkoholhaltige Getränke": "sweets_snacks_drinks",
    "Gerichte": "mixed",
    "Verschiedenes": "mixed",
    "Speziallebensmittel": "mixed",
}


def group_for(category: str) -> str:
    top, _, sub = str(category).partition("/")
    if top == "Alkoholfreie Getränke":
        return "sweets_snacks_drinks" if "Süss" in sub or "Fruchtsaft" in sub or "Sirup" in sub else "drinks_unsweetened"
    return CATEGORY_TO_GROUP.get(top, "mixed")


@dataclass
class Verdict:
    ok: bool
    rule: str | None = None
    detail: str | None = None


def atwater_kcal(n: dict) -> float | None:
    """Energy from macronutrients per 100 g (EU factors)."""
    try:
        return 4 * n["proteins"] + 4 * n["carbohydrates"] + 9 * n["fat"] + 2 * (n.get("fiber") or 0)
    except (KeyError, TypeError):
        return None


def check_energy(n: dict, tol: float = 0.25, slack_kcal: float = 25) -> Verdict:
    """Printed kcal must agree with the macronutrients within 25% or 25 kcal."""
    stated, computed = n.get("energy_kcal"), atwater_kcal(n)
    if stated is None or computed is None:
        return Verdict(True)
    if abs(stated - computed) <= max(slack_kcal, tol * max(stated, computed)):
        return Verdict(True)
    alcohol_room = stated - computed
    if 0 < alcohol_room < 0.6 * stated and n.get("alcohol_hint"):
        return Verdict(True)
    return Verdict(False, "atwater", f"label says {stated:.0f} kcal, macronutrients give {computed:.0f} kcal")


LIQUID_GROUPS = {"dairy", "sweets_snacks_drinks", "drinks_unsweetened", "fats_nuts", "mixed"}


def check_unit(line_is_volume: bool, food_is_liquid: bool, group: str) -> Verdict:
    """A line sold in litres cannot be a solid food, and vice versa (with known exceptions)."""
    if line_is_volume and not food_is_liquid and group not in LIQUID_GROUPS:
        return Verdict(False, "unit", "sold by volume but the food is a solid")
    if line_is_volume and not food_is_liquid and group == "dairy":
        return Verdict(False, "unit", "sold by volume but the dairy food is solid (e.g. cheese)")
    return Verdict(True)


def check_pack(pack_grams: float | None, group: str) -> Verdict:
    """Pack sizes far outside what a household buys suggest a wrong reading."""
    if pack_grams is None:
        return Verdict(True)
    if pack_grams > 25000:
        return Verdict(False, "pack", f"{pack_grams:.0f} g is not a household pack")
    return Verdict(True)


# Swiss food words that a model trained mostly on standard German, French and Italian
# misreads. Apertus 8B read "RUEBLI" (carrot) as kale in our first test. Each entry maps a
# receipt word to the FSVO naming. Sources: Duden "Schweizerhochdeutsch" and FSVO synonyms.
HELVETISMS = {
    "ruebli": "Karotte (Rüebli)", "rüebli": "Karotte (Rüebli)", "peperoni": "Peperoni Paprika", "nuesslisalat": "Feldsalat Nüsslisalat",
    "nüsslisalat": "Feldsalat Nüsslisalat", "rahm": "Rahm Sahne", "halbrahm": "Halbrahm", "vollrahm": "Vollrahm",
    "gipfeli": "Gipfel Croissant", "zopf": "Zopf", "cervelat": "Cervelat", "wienerli": "Wienerli Wurst",
    "chips": "Chips Kartoffelchips", "poulet": "Poulet Huhn", "glace": "Glace Speiseeis", "konfi": "Konfitüre",
    "znüni": "", "harass": "", "pastmilch": "Vollmilch pasteurisiert", "past": "pasteurisiert",
    "kefe": "Kefen Zuckererbsen", "kefen": "Kefen Zuckererbsen", "randen": "Randen Rote Bete", "federkohl": "Federkohl Grünkohl",
    "rüebli-": "Karotte", "anke": "Butter", "nidle": "Rahm", "härdöpfel": "Kartoffel", "erdäpfel": "Kartoffel",
    "lait": "Milch", "fromage": "Käse", "pâtes": "Teigwaren", "pates": "Teigwaren", "riz": "Reis", "beurre": "Butter",
    "pommes de terre": "Kartoffel", "carottes": "Karotte", "pomodori": "Tomate", "pelati": "Tomaten geschält",
    "latte": "Milch", "formaggio": "Käse", "burro": "Butter", "pane": "Brot", "pain": "Brot", "mele": "Apfel",
    "pommes": "Apfel", "poires": "Birne", "pere": "Birne", "uova": "Ei", "oeufs": "Ei", "yogourt": "Joghurt",
    "yogurt": "Joghurt", "jogurt": "Joghurt", "salami": "Salami", "prosciutto": "Rohschinken Schinken",
}


def helvetism_hints(text: str) -> list[str]:
    low = text.lower()
    return [v for k, v in HELVETISMS.items() if v and re.search(rf"(?<![a-zäöü]){re.escape(k)}(?![a-zäöü])", low)]
