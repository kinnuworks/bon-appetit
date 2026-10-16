"""Fill the result placeholders in README.md and technical_report.md from eval/results.json."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
r = json.loads((ROOT / "eval/results.json").read_text())
off = json.loads((ROOT / "eval/off_energy_summary.json").read_text())
m = {x["id"]: x for x in r["methods"]}
pct = lambda v: "n/a" if v is None else f"{round(100 * v)}%"
num = lambda v, d=0: "n/a" if v is None else (f"{v:.{d}f}")

rows = ["| Method | kcal error per 100 g (95% CI) | Off by >100 kcal | Sugar error, g | Salt error, g | Food group right | Abstains |",
        "|---|---|---|---|---|---|---|"]
for k in ["fuzzy", "embed", "retrieval", "apertus_only", "hybrid", "oracle"]:
    x = m[k]
    ci = x.get("kcal_ci") or [None, None]
    rows.append(f"| {x['label']} | {num(x['kcal_mae'])} ({num(ci[0])} to {num(ci[1])}) | {pct(x.get('over100_kcal'))} | "
                f"{num(x['sugar_mae'], 1)} | {num(x['salt_mae'], 2)} | {pct(x['group_acc'])} | {pct(x['abstain'])} |")
mt = ["| Method, on the products the hybrid answered | n | kcal error (95% CI) | Off by >100 kcal |", "|---|---|---|---|"]
for x in r.get("matched", []):
    ci = x.get("kcal_ci") or [None, None]
    mt.append(f"| {x['label']} | {x['n']} | {num(x['kcal_mae'])} ({num(ci[0])} to {num(ci[1])}) | {pct(x.get('over100_kcal'))} |")
table = "\n".join(rows) + "\n\n" + "\n".join(mt)

langs = ["| Language | n | Fuzzy kcal error | Embeddings kcal error | Apertus alone kcal error | Hybrid kcal error | Hybrid food group right |", "|---|---|---|---|---|---|---|"]
for lg in ["de", "fr", "it"]:
    by = {x["id"]: x for x in r["by_lang"] if x["lang"] == lg}
    if by:
        langs.append(f"| {lg.upper()} | {by['hybrid']['n']} | {num(by['fuzzy']['kcal_mae'])} | {num(by['embed']['kcal_mae'])} | "
                     f"{num(by['apertus_only']['kcal_mae'])} | {num(by['hybrid']['kcal_mae'])} | {pct(by['hybrid']['group_acc'])} |")
by_lang = ("**By language.** The Italian sample is small, so its numbers carry wide uncertainty.\n\n" + "\n".join(langs))

h, f, a, o, rt = m["hybrid"], m["fuzzy"], m["apertus_only"], m["oracle"], m["retrieval"]
cut = round(100 * (1 - h["kcal_mae"] / f["kcal_mae"]))
pick_cut = round(100 * (1 - h["kcal_mae"] / rt["kcal_mae"]))
summary = (f"the hybrid's energy estimate is off by {num(h['kcal_mae'])} kcal per 100 g on average, {cut}% less than fuzzy text "
           f"matching ({num(f['kcal_mae'])}), and it names the right food group for {pct(h['group_acc'])} of products against "
           f"{pct(f['group_acc'])}. Apertus's pick is what does it: search alone, without the pick, is off by {num(rt['kcal_mae'])}, "
           f"so the pick cuts the error by {pick_cut}%. Apertus guessing the numbers itself lands close ({num(a['kcal_mae'])}) but gives no source "
           f"that anyone could check or correct.")
headline = (f"On {r['n_products']} real Swiss products it cuts the energy error of text matching by {cut}%, nearly doubles the share of "
            f"products put in the right food group, and every number it reports traces to a federal food record.")
off_line = (f"Running the same energy check over all {off['checked']:,} Swiss products on Open Food Facts flagged "
            f"{off['flagged']:,} ({pct(off['share'])}) whose printed calories contradict their own macronutrients; "
            f"{off['looks_like_kj_typed_as_kcal']} look like kilojoules typed as kilocalories. The list is in `eval/off_energy_flags.csv`.")
results_md = (f"{r['n_products']} real Swiss products from Open Food Facts, label hidden, receipt-style line in, compared with the printed "
              f"label ({r.get('notes', '')}).\n\n{table}\n\n{off_line}\n\nThe oracle row is the best any link to a generic FSVO "
              f"food can do; the gap between it and the hybrid is linking error, which is where the next work goes.")
lesson = (f"Apertus alone produced plausible numbers for every product ({num(a['kcal_mae'])} kcal mean error) but cannot say "
          f"where they came from. In the hybrid it never writes a number, so every value in the household report can be checked.")

c = r.get("cost") or {}
cost = (f"Measured on an Apple M5 laptop with 16 GB, Apertus v1.5 8B Q4_K_M through Ollama, four requests in parallel: "
        f"{num(c.get('sec_per_line'), 1)} seconds per receipt line for both calls together, including queueing. A weekly receipt of "
        f"20 food lines therefore takes about {num((c.get('sec_per_line') or 0) * 20 / 60, 1)} minutes on one laptop, with no "
        f"subscription and no per-request fee. Electricity for 1,000 such receipts is about CHF {num(c.get('chf_per_1000_receipts'), 2)} "
        f"({c.get('cost_assumptions', '')}). A server GPU or a Swiss cloud endpoint serving the 8B model is many times faster; "
        f"that is the path for a retailer-scale service.")

for name in ["README.md", "technical_report.md"]:
    p = ROOT / name
    s = p.read_text()
    s = (s.replace("{{RESULTS}}", results_md).replace("{{RESULTS_TABLE}}", table + "\n\n" + off_line)
          .replace("{{BY_LANG}}", by_lang).replace("{{N}}", str(r["n_products"])).replace("{{SUMMARY_RESULT}}", summary)
          .replace("{{HEADLINE}}", headline).replace("{{LESSON_NUMBERS}}", lesson).replace("{{COST}}", cost)
          .replace("{{GGUF_SHA}}", "a037df8d87ff6caacee794ee85f55342f2152e0d359b7389033300c3bee5f299"))
    p.write_text(s)
print("filled", headline)
