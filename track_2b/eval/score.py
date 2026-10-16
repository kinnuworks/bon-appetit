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
from bonappetit.linker import cross_check

ROOT = Path(__file__).resolve().parents[1]
GOLD, PRED = ROOT / "eval/gold.jsonl", ROOT / "eval/predictions.jsonl"
KEYS = ["energy_kcal", "sugars", "salt", "fat", "proteins", "carbohydrates"]
OFF_GROUP = {
    "en:fruits-and-vegetables": "vegetables_fruit", "en:cereals-and-potatoes": "grains_potatoes",
    "en:milk-and-dairy-products": "dairy", "en:fish-meat-eggs": "protein", "en:fat-and-sauces": "fats_nuts",
    "en:sugary-snacks": "sweets_snacks_drinks", "en:salty-snacks": "sweets_snacks_drinks",
    "en:composite-foods": "mixed",
}
LABELS = {"fuzzy": "Fuzzy text match", "embed": "Swiss embeddings only",
          "retrieval": "Search only, no Apertus pick (ablation)", "apertus_only": "Apertus alone, guessing (no source)",
          "hybrid": "Hybrid, Apertus pick only", "checked": "Bon·Appétit: pick plus Apertus cross-check", "oracle": "Label-informed ceiling (best FSVO food)"}


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


def rnd(x, n=1):
    return None if x is None else round(x, n)


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
        cands = p["hybrid"].get("candidates") or []
        hid = p["hybrid"]["fsvo_id"]
        checked = cross_check(hid, cands, p.get("apertus_only") or {}, lambda i: nut[i]) if hid else None
        picks = {"fuzzy": p["fuzzy"], "embed": p["embed"], "oracle": oracle(lab), "checked": checked,
                 "retrieval": cands[0] if cands else None,
                 "hybrid": p["hybrid"]["fsvo_id"] if p["hybrid"]["status"] in ("linked", "vetoed", "review") and p["hybrid"]["fsvo_id"] else None}
        for m, fid in picks.items():
            if fid is None:
                rows[m].append({"lang": lang, "abstain": True})
                continue
            e = err(nut[fid], lab)
            grp = group_for(cat.row(fid)["category"])
            rows[m].append({"lang": lang, "barcode": p["barcode"], "abstain": False, "e": e, "group_ok": None if gg is None else grp == gg,
                            "review": m == "hybrid" and p["hybrid"]["status"] == "review", "idx": len(rows[m])})
        guess = p.get("apertus_only") or {}
        if guess.get("energy_kcal") is None:
            rows["apertus_only"].append({"lang": lang, "abstain": True})
        else:
            rows["apertus_only"].append({"lang": lang, "barcode": p["barcode"], "abstain": False, "e": err(guess, lab), "group_ok": None})

    def summarise(rs):
        ans = [r for r in rs if not r["abstain"]]
        kcal = [r["e"]["energy_kcal"] for r in ans if "energy_kcal" in r["e"]]
        g_ok = [r["group_ok"] for r in ans if r["group_ok"] is not None]
        return {
            "n": len(rs), "answered": len(ans),
            "abstain": round(1 - len(ans) / len(rs), 3) if rs else None,
            "kcal_mae": rnd(mean(kcal), 1), "kcal_ci": boot_ci(kcal),
            "sugar_mae": rnd(mean([r["e"].get("sugars") for r in ans]), 2),
            "salt_mae": rnd(mean([r["e"].get("salt") for r in ans]), 2),
            "fat_mae": rnd(mean([r["e"].get("fat") for r in ans]), 2),
            "group_acc": rnd(mean([1.0 if x else 0.0 for x in g_ok]), 3),
        }

    labs = [gold[p["barcode"]]["label"]["energy_kcal"] for p in preds]
    methods = []
    for m, rs in rows.items():
        s = summarise(rs)
        within = [not r["abstain"] and r["e"].get("energy_kcal", 1e9) <= max(0.2 * k, 20) for r, k in zip(rs, labs)]
        s["within20_kcal"] = round(sum(within) / len(within), 3) if within else None
        answered = [r for r in rs if not r["abstain"] and "energy_kcal" in r["e"]]
        s["over100_kcal"] = rnd(mean([1.0 if r["e"]["energy_kcal"] > 100 else 0.0 for r in answered]), 3)
        s.update({"id": m, "label": LABELS[m]})
        if m in ("hybrid", "checked"):
            s["review_share"] = rnd(mean([1.0 if r.get("review") else 0.0 for r in rs]), 3)
        methods.append(s)
    # Matched subset: every method scored on exactly the products the hybrid answered.
    hyb_ok = {r["barcode"] for r in rows["hybrid"] if not r["abstain"]}
    matched = []
    for m in ["fuzzy", "embed", "retrieval", "apertus_only", "hybrid", "checked", "oracle"]:
        sub = [r for r in rows[m] if not r["abstain"] and r.get("barcode") in hyb_ok and "energy_kcal" in r["e"]]
        kc = [r["e"]["energy_kcal"] for r in sub]
        matched.append({"id": m, "label": LABELS[m], "n": len(sub), "kcal_mae": rnd(mean(kc), 1), "kcal_ci": boot_ci(kc),
                        "over100_kcal": rnd(mean([1.0 if k > 100 else 0.0 for k in kc]), 3)})
    # Held-out check for the cross-check: its two settings were chosen on the odd-numbered products
    # (in prediction order); this scores every method on the even-numbered ones only.
    even = {p["barcode"] for p in preds[0::2]}
    heldout = []
    for m in ["fuzzy", "retrieval", "apertus_only", "hybrid", "checked", "oracle"]:
        kc = [r["e"]["energy_kcal"] for r in rows[m] if not r["abstain"] and r.get("barcode") in even and "energy_kcal" in r["e"]]
        heldout.append({"id": m, "label": LABELS[m], "n": len(kc), "kcal_mae": rnd(mean(kc), 1), "kcal_ci": boot_ci(kc)})

    # Paired comparison on the same products: Bon·Appétit minus Apertus guessing alone (negative = Bon·Appétit better).
    def paired(a_id, b_id, keep=None):
        ea = {r["barcode"]: r["e"]["energy_kcal"] for r in rows[a_id] if not r["abstain"] and "energy_kcal" in r["e"]}
        eb = {r["barcode"]: r["e"]["energy_kcal"] for r in rows[b_id] if not r["abstain"] and "energy_kcal" in r["e"]}
        common = [b for b in ea if b in eb and (keep is None or b in keep)]
        diffs = [ea[b] - eb[b] for b in common]
        return {"a": a_id, "b": b_id, "n": len(diffs), "mean_diff": rnd(mean(diffs), 1), "ci95": boot_ci(diffs, n=2000),
                "a_better_share": rnd(mean([1.0 if d < 0 else 0.0 for d in diffs]), 3)}
    pairs = [paired("checked", "apertus_only"), paired("checked", "apertus_only", even), paired("checked", "fuzzy"),
             paired("checked", "hybrid")]

    # Household view: 200 random baskets of 20 products. Compare the food-pyramid shares the method reports
    # (grams by the linked food's group, 100 g per product) with the shares from the products' own Open Food Facts
    # groups. This is the number a household actually sees.
    rng = random.Random(11)
    truth_group = {p["barcode"]: off_group(gold[p["barcode"]]["food_groups"]) for p in preds}
    link_group = {m: {} for m in ["fuzzy", "embed", "retrieval", "hybrid", "checked"]}
    for p in preds:
        cands = p["hybrid"].get("candidates") or []
        hid = p["hybrid"]["fsvo_id"] if p["hybrid"]["fsvo_id"] else None
        ids = {"fuzzy": p["fuzzy"], "embed": p["embed"], "retrieval": cands[0] if cands else None, "hybrid": hid,
               "checked": cross_check(hid, cands, p.get("apertus_only") or {}, lambda i: nut[i]) if hid else None}
        for m, fid in ids.items():
            link_group[m][p["barcode"]] = None if fid is None else group_for(cat.row(fid)["category"])
    pool = [b for b, g in truth_group.items() if g]
    pyr = ["vegetables_fruit", "grains_potatoes", "dairy", "protein", "fats_nuts", "sweets_snacks_drinks", "mixed"]
    baskets = [rng.sample(pool, min(20, len(pool))) for _ in range(200)]
    household = []
    for m in link_group:
        errs = []
        for bk in baskets:
            t = [truth_group[b] for b in bk]
            e = [link_group[m][b] for b in bk if link_group[m][b]]
            if not e:
                continue
            errs.append(mean([abs(t.count(g) / len(t) - e.count(g) / len(e)) * 100 for g in pyr]))
        household.append({"id": m, "label": LABELS[m], "share_error_pp": rnd(mean(errs), 1), "baskets": len(errs)})

    # Sensitivity: drop products whose own printed label fails the energy check.
    def label_ok(lab):
        comp = 4 * lab["proteins"] + 4 * lab["carbohydrates"] + 9 * lab["fat"]
        return abs(lab["energy_kcal"] - comp) <= max(25, 0.25 * max(lab["energy_kcal"], comp))
    clean = {p["barcode"] for p in preds if label_ok(gold[p["barcode"]]["label"])}
    sensitivity = []
    for m in ["fuzzy", "retrieval", "apertus_only", "hybrid", "checked", "oracle"]:
        kc = [r["e"]["energy_kcal"] for r in rows[m] if not r["abstain"] and r.get("barcode") in clean and "energy_kcal" in r["e"]]
        sensitivity.append({"id": m, "n": len(kc), "kcal_mae": rnd(mean(kc), 1)})
    by_lang = []
    for lang in ["de", "fr", "it"]:
        for m in ["fuzzy", "embed", "apertus_only", "hybrid", "checked"]:
            rs = [r for r in rows[m] if r["lang"] == lang]
            if rs:
                s = summarise(rs)
                by_lang.append({"lang": lang, "id": m, "n": s["n"], "kcal_mae": s["kcal_mae"], "group_acc": s["group_acc"]})
    stats = json.load(open(ROOT / "eval/run_stats.json")) if (ROOT / "eval/run_stats.json").exists() else {}
    secs = [p.get("hybrid_seconds") for p in preds if p.get("hybrid_seconds")]
    # Cost on the laptop: measured seconds per line, 30 W package power under load (Apple M-series, stated
    # assumption), 20 food lines per weekly receipt, CHF 0.30 per kWh (Swiss household average, assumption).
    spl = mean(secs) if secs else None
    chf_1000 = None if spl is None else round(spl * 20 * 1000 * 30 / 3.6e6 * 0.30, 2)
    res = {"status": "done", "n_products": len(preds), "n_planned": len(gold), "methods": methods, "heldout": heldout, "paired": pairs, "matched": matched, "household": household, "sensitivity": sensitivity,
           "labels_failing_energy_check": len(preds) - len(clean), "by_lang": by_lang,
           "cost": {"sec_per_line": rnd(spl, 1), "chf_per_1000_receipts": chf_1000,
                    "cost_assumptions": "laptop at 30 W, 20 food lines per receipt, CHF 0.30 per kWh, measured seconds per line with 4 parallel requests", "hardware": "Apple M5, 16 GB, Ollama, Q4_K_M",
                    "model": stats.get("model"), "tokens_in": stats.get("tokens_in"), "tokens_out": stats.get("tokens_out")},
           "notes": "Errors are per 100 g against printed Open Food Facts labels. Within-20% uses max(20% of label, 20 kcal)."}
    blob = json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True)
    (ROOT / "eval/results.json").write_text(blob)
    (ROOT / "site/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "site/data/results.json").write_text(blob)
    digest = hashlib.sha256(blob.encode()).hexdigest()
    print(f"{'method':28s} {'n':>4s} {'kcal MAE':>9s} {'95% CI':>14s} {'sugar':>6s} {'salt':>6s} {'≤20%':>6s} {'group':>6s} {'abstain':>7s}")
    print("paired:", [(x["a"], x["b"], x["n"], x["mean_diff"], x["ci95"]) for x in pairs])
    print("held-out half:", [(x["id"], x["n"], x["kcal_mae"]) for x in heldout])
    print("household share error (pp):", [(x["id"], x["share_error_pp"]) for x in household])
    print("sensitivity:", [(x["id"], x["n"], x["kcal_mae"]) for x in sensitivity])
    print("matched subset:", [(x["id"], x["n"], x["kcal_mae"], x["over100_kcal"]) for x in matched])
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
