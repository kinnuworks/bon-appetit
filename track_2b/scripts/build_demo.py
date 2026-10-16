"""Run the real pipeline over the three demo receipts and write site/data/demo.json."""
import json
from concurrent.futures import ThreadPoolExecutor

from bonappetit.catalog import Catalog
from bonappetit.ledger import nudge, summarise
from bonappetit.linker import Linker
from bonappetit.llm import Apertus
from bonappetit.receipt import make_line

SRC = "site/data/demo.json"
sample = json.load(open(SRC))
cat, llm = Catalog(use_embeddings=True), Apertus()
linker = Linker(cat, llm)
PYR = ["vegetables_fruit", "grains_potatoes", "dairy", "protein", "fats_nuts", "sweets_snacks_drinks"]

out = {"note": "Real output of the Bon·Appétit pipeline (Apertus v1.5 8B, local) on three example receipts written for this demo.",
       "receipts": [], "summary": {}}
for rc in sample["receipts"]:
    lines = [make_line(l["raw"], qty=l.get("qty", 1), price=l.get("price"), shop=rc.get("shop")) for l in rc["lines"]]
    with ThreadPoolExecutor(4) as ex:
        links = list(ex.map(lambda l: linker.link(l).to_dict(), lines))
    hh = rc.get("household_size", 1)
    days = rc.get("days", 7)
    s = summarise(links, cat, adults=hh, days=days)
    view = []
    for l in links:
        c = l.get("choice") or {}
        item = {"raw": l["line"]["text"], "qty": l["line"]["qty"], "price": l["line"]["price"],
                "decoded": (l.get("read") or {}).get("english", ""), "status": "review" if l["status"] == "review" else
                ("nonfood" if l["status"] == "nonfood" else "linked")}
        if c:
            item["match"] = {"source": "fsvo", "id": c["fsvo_id"], "name": c["name"], "group": c["group"]}
            item["grams"] = round((l["line"]["pack_grams"] or 0) * (l["line"]["qty"] or 1))
        if l.get("veto"):
            item["veto"] = l["veto"]
        if l["status"] == "review":
            item["question"] = l.get("question")
            item["candidates"] = [{"name": x["name"]} for x in l.get("candidates", [])[:3]]
        if l["status"] == "nonfood":
            item["reason"] = "Not a food or drink"
        view.append(item)
    out["receipts"].append({**{k: rc[k] for k in rc if k != "lines"}, "lines": view})
    total = sum(s["grams_per_adult_day"][g] for g in PYR) or 1
    ref_total = sum(s["reference_per_adult_day"][g] for g in PYR)
    out["summary"][rc["id"]] = {
        "pyramid": {g: round(s["grams_per_adult_day"][g] / total, 3) for g in PYR},
        "recommended": {g: round(s["reference_per_adult_day"][g] / ref_total, 3) for g in PYR},
        "grams_per_adult_day": s["grams_per_adult_day"],
        "sugar_g_per_day": s["per_adult_day"]["sugars"], "salt_g_per_day": s["per_adult_day"]["salt"],
        "satfat_g_per_day": s["per_adult_day"]["saturated_fat"],
        "fruit_veg_portions_per_day": round(s["grams_per_adult_day"]["vegetables_fruit"] / 120, 1),
        "lines": {k: s[k] for k in ("lines_total", "lines_linked", "lines_review", "lines_nonfood")},
        "nudges": [{"lang": lg, "text": nudge(s, llm, lg)} for lg in ("de", "fr", "it", "en")],
    }
    print(rc["id"], s["lines_linked"], "linked,", s["lines_review"], "review", flush=True)
json.dump(out, open(SRC, "w"), ensure_ascii=False, indent=1)
