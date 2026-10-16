"""Score stored predictions against printed labels. Needs no model and no network.

Writes eval/results.json and site/data/results.json, then checks the results against
eval/results.sha256 so a judge can confirm the numbers in the report came from this code.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

from bonappetit.catalog import Catalog
from bonappetit.foodlayer import group_for

ROOT = Path(__file__).resolve().parents[1]
GOLD, PRED = ROOT / "eval/gold.jsonl", ROOT / "eval/predictions.jsonl"
KEYS = ["energy_kcal", "sugars", "salt", "fat", "proteins", "carbohydrates"]
OFF_GROUP = {
    "en:fruits-and-vegetables": "vegetables_fruit", "en:cereals-and-potatoes": "grains_potatoes",
    "en:milk-and-dairy-products": "dairy", "en:fish-meat-eggs": "protein", "en:fat-and-sauces": "fats_nuts",
    "en:sugary-snacks": "sweets_snacks_drinks", "en:salty-snacks": "sweets_snacks_drinks",
    "en:composite-foods": "mixed",
}
LABELS = {"fuzzy": "Fuzzy text match", "embed": "Swiss embeddings only", "apertus_only": "Apertus alone, guessing",
          "hybrid": "Bon·Appétit hybrid", "oracle": "Oracle (best FSVO food)"}


def off_group(tags):
    for t in tags or []:
        if t in OFF_GROUP:
            return OFF_GROUP[t]
    if any(t.startswith("en:beverages") or t.startswith("en:sweetened") for t in tags or []):
        return "sweets_snacks_drinks"
    return None


def err(est, lab):
    return {k: abs((est.get(k) or 0) - lab[k]) for k in KEYS if est.get(k) is not None}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def boot_ci(xs, n=1000, seed=7):
    rnd = random.Random(seed)
    if not xs:
        return [None, None]
    ms = sorted(mean([rnd.choice(xs) for _ in xs]) for _ in range(n))
    return [round(ms[int(0.025 * n)], 1), round(ms[int(0.975 * n)], 1)]


def main(check: bool = True) -> int:
    cat = Catalog(use_embeddings=False)
    gold = {g["barcode"]: g for g in map(json.loads, open(GOLD))}
    preds = [json.loads(l) for l in open(PRED)]
    nut = {i: cat.nutrients(i) for i in cat.df.fsvo_id}

    def oracle(lab):
        def d(i):
            n = nut[i]
            return sum(abs((n.get(k) or 0) - lab[k]) / s for k, s in [("energy_kcal", 100), ("sugars", 10), ("fat", 10), ("proteins", 10)])
        return min(nut, key=d)

    rows = {m: [] for m in LABELS}
    for p in preds:
        g = gold[p["barcode"]]
        lab, lang, gg = g["label"], g["lang"], off_group(g["food_groups"])
        picks = {"fuzzy": p["fuzzy"], "embed": p["embed"], "oracle": oracle(lab),
                 "hybrid": p["hybrid"]["fsvo_id"] if p["hybrid"]["status"] in ("linked", "vetoed", "review") and p["hybrid"]["fsvo_id"] else None}
        for m, fid in picks.items():
            if fid is None:
                rows[m].append({"lang": lang, "abstain": True})
                continue
            e = err(nut[fid], lab)
            grp = group_for(cat.row(fid)["category"])
            rows[m].append({"lang": lang, "abstain": False, "e": e, "group_ok": None if gg is None else grp == gg,
                            "review": m == "hybrid" and p["hybrid"]["status"] == "review"})
        guess = p.get("apertus_only") or {}
        if guess.get("energy_kcal") is None:
            rows["apertus_only"].append({"lang": lang, "abstain": True})
        else:
            rows["apertus_only"].append({"lang": lang, "abstain": False, "e": err(guess, lab), "group_ok": None})

    def summarise(rs):
        ans = [r for r in rs if not r["abstain"]]
        kcal = [r["e"]["energy_kcal"] for r in ans if "energy_kcal" in r["e"]]
        g_ok = [r["group_ok"] for r in ans if r["group_ok"] is not None]
        return {
            "n": len(rs), "answered": len(ans),
            "abstain": round(1 - len(ans) / len(rs), 3) if rs else None,
            "kcal_mae": round(mean(kcal), 1) if kcal else None, "kcal_ci": boot_ci(kcal),
            "sugar_mae": round(mean([r["e"].get("sugars") for r in ans]), 2) if ans else None,
            "salt_mae": round(mean([r["e"].get("salt") for r in ans]), 2) if ans else None,
            "fat_mae": round(mean([r["e"].get("fat") for r in ans]), 2) if ans else None,
            "group_acc": round(mean([1.0 if x else 0.0 for x in g_ok]), 3) if g_ok else None,
        }

    labs = [gold[p["barcode"]]["label"]["energy_kcal"] for p in preds]
    methods = []
    for m, rs in rows.items():
        s = summarise(rs)
        within = [not r["abstain"] and r["e"].get("energy_kcal", 1e9) <= max(0.2 * k, 20) for r, k in zip(rs, labs)]
        s["within20_kcal"] = round(sum(within) / len(within), 3) if within else None
        s.update({"id": m, "label": LABELS[m]})
        if m == "hybrid":
            s["review_share"] = round(mean([1.0 if r.get("review") else 0.0 for r in rs]), 3)
        methods.append(s)
    by_lang = []
    for lang in ["de", "fr", "it"]:
        for m in ["fuzzy", "embed", "apertus_only", "hybrid"]:
            rs = [r for r in rows[m] if r["lang"] == lang]
            if rs:
                s = summarise(rs)
                by_lang.append({"lang": lang, "id": m, "n": s["n"], "kcal_mae": s["kcal_mae"], "group_acc": s["group_acc"]})
    stats = json.load(open(ROOT / "eval/run_stats.json")) if (ROOT / "eval/run_stats.json").exists() else {}
    secs = [p.get("hybrid_seconds") for p in preds if p.get("hybrid_seconds")]
    res = {"status": "done", "n_products": len(preds), "methods": methods, "by_lang": by_lang,
           "cost": {"sec_per_line": round(mean(secs), 1) if secs else None, "hardware": "Apple M5, 16 GB, Ollama, Q4_K_M",
                    "model": stats.get("model"), "tokens_in": stats.get("tokens_in"), "tokens_out": stats.get("tokens_out")},
           "notes": "Errors are per 100 g against printed Open Food Facts labels. Within-20% uses max(20% of label, 20 kcal)."}
    blob = json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True)
    (ROOT / "eval/results.json").write_text(blob)
    (ROOT / "site/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "site/data/results.json").write_text(blob)
    digest = hashlib.sha256(blob.encode()).hexdigest()
    print(f"{'method':28s} {'n':>4s} {'kcal MAE':>9s} {'95% CI':>14s} {'sugar':>6s} {'salt':>6s} {'≤20%':>6s} {'group':>6s} {'abstain':>7s}")
    for s in methods:
        print(f"{s['label']:28s} {s['n']:4d} {str(s['kcal_mae']):>9s} {str(s['kcal_ci']):>14s} {str(s['sugar_mae']):>6s} "
              f"{str(s['salt_mae']):>6s} {str(s['within20_kcal']):>6s} {str(s['group_acc']):>6s} {str(s['abstain']):>7s}")
    ref = ROOT / "eval/results.sha256"
    if check and ref.exists():
        ok = ref.read_text().split()[0] == digest
        print("results hash", "matches eval/results.sha256" if ok else f"DIFFERS: {digest}")
        return 0 if ok else 1
    ref.write_text(digest + "  eval/results.json\n")
    print("wrote", ref.name, digest[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--update" not in sys.argv))
