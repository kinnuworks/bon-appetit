"""Flag Swiss Open Food Facts entries whose printed energy disagrees with their macronutrients.

Rule (EU factors): kcal ≈ 4·protein + 4·carbohydrate + 9·fat + 2·fibre (+ 7·alcohol, unknown here,
so drinks with alcohol are skipped). Flag when the gap exceeds both 25% and 25 kcal per 100 g.
Output: eval/off_energy_flags.csv (barcode, name, printed, computed), ODbL like its source.
"""
import json
import pandas as pd

df = pd.read_parquet("data/off_ch.parquet")
need = ["energy_kcal", "fat", "carbohydrates", "proteins"]
d = df.dropna(subset=need).copy()
d = d[~d["categories_tags"].map(lambda t: t is not None and any("alcohol" in x or "beer" in x or "wine" in x for x in t))]
d["fiber"] = d["fiber"].fillna(0)
d["computed"] = 4 * d.proteins + 4 * d.carbohydrates + 9 * d.fat + 2 * d.fiber
gap = (d.energy_kcal - d.computed).abs()
d["flag"] = (gap > 25) & (gap > 0.25 * d[["energy_kcal", "computed"]].max(axis=1))
d["kj_as_kcal"] = d.flag & ((d.energy_kcal / d.computed.clip(lower=1)).between(3.8, 4.6))
name = d["product_name"].map(lambda v: next((n["text"] for n in v if n["text"]), "") if v is not None else "")
flags = d[d.flag].assign(name=name).loc[:, ["code", "name", "energy_kcal", "computed", "kj_as_kcal"]]
flags["computed"] = flags["computed"].round(0)
flags.to_csv("eval/off_energy_flags.csv", index=False)
summary = {"checked": int(len(d)), "flagged": int(d.flag.sum()), "share": round(float(d.flag.mean()), 4),
           "looks_like_kj_typed_as_kcal": int(d.kj_as_kcal.sum())}
json.dump(summary, open("eval/off_energy_summary.json", "w"), indent=2)
print(summary)
