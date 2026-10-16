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
for k in ["fuzzy", "embed", "retrieval", "apertus_only", "hybrid", "checked", "oracle"]:
    x = m[k]
    ci = x.get("kcal_ci") or [None, None]
    rows.append(f"| {x['label']} | {num(x['kcal_mae'])} ({num(ci[0])} to {num(ci[1])}) | {pct(x.get('over100_kcal'))} | "
                f"{num(x['sugar_mae'], 1)} | {num(x['salt_mae'], 2)} | {pct(x['group_acc'])} | {pct(x['abstain'])} |")
ho = ["| Method, held-out half only | n | kcal error (95% CI) |", "|---|---|---|"]
for x in r.get("heldout", []):
    ci = x.get("kcal_ci") or [None, None]
    ho.append(f"| {x['label']} | {x['n']} | {num(x['kcal_mae'])} ({num(ci[0])} to {num(ci[1])}) |")
mt = ["| Method, on the products the hybrid answered | n | kcal error (95% CI) | Off by >100 kcal |", "|---|---|---|---|"]
for x in r.get("matched", []):
    ci = x.get("kcal_ci") or [None, None]
    mt.append(f"| {x['label']} | {x['n']} | {num(x['kcal_mae'])} ({num(ci[0])} to {num(ci[1])}) | {pct(x.get('over100_kcal'))} |")
table = ("\n".join(rows) + "\n\n**Held-out check.** The cross-check has two settings (how many candidates it looks at, and how strongly "
         "it favours the model's own pick). They were chosen on the odd-numbered products only; this table scores every method on the "
         "even-numbered products, which played no part in that choice.\n\n" + "\n".join(ho) + "\n\n" + "\n".join(mt))

langs = ["| Language | n | Fuzzy kcal error | Embeddings kcal error | Apertus alone kcal error | Hybrid kcal error | Hybrid food group right |", "|---|---|---|---|---|---|---|"]
for lg in ["de", "fr", "it"]:
    by = {x["id"]: x for x in r["by_lang"] if x["lang"] == lg}
    if by:
        langs.append(f"| {lg.upper()} | {by['checked']['n']} | {num(by['fuzzy']['kcal_mae'])} | {num(by['embed']['kcal_mae'])} | "
                     f"{num(by['apertus_only']['kcal_mae'])} | {num(by['checked']['kcal_mae'])} | {pct(by['checked']['group_acc'])} |")
by_lang = ("**By language** (Bon·Appétit = pick plus cross-check). German and French gain clearly. Italian does not: with 30 "
           "products it is no better than Apertus guessing, and only a quarter land in the right food group. The Italian sample is "
           "small, and Italian shop shorthand is the next thing to work on.\n\n" + "\n".join(langs))

h, f, a, o, rt, hp = m["checked"], m["fuzzy"], m["apertus_only"], m["oracle"], m["retrieval"], m["hybrid"]
cut = round(100 * (1 - h["kcal_mae"] / f["kcal_mae"]))
pick_cut = round(100 * (1 - hp["kcal_mae"] / rt["kcal_mae"]))
hold = {x["id"]: x for x in r.get("heldout", [])}
hold_cut = round(100 * (1 - hold["checked"]["kcal_mae"] / hold["apertus_only"]["kcal_mae"])) if hold else None
hh = {x["id"]: x for x in r.get("household", [])}
summary = (f"Bon·Appétit's energy estimate is off by {num(h['kcal_mae'])} kcal per 100 g on average, {cut}% less than fuzzy text "
           f"matching ({num(f['kcal_mae'])}) and less than Apertus guessing the numbers itself ({num(a['kcal_mae'])}), which gives no source. "
           f"On the held-out half, where nothing was tuned, the gap to Apertus guessing is {hold_cut}%. Only {pct(h.get('over100_kcal'))} "
           f"of products are off by more than 100 kcal, against {pct(f.get('over100_kcal'))} for text matching. Both Apertus steps matter: "
           f"the pick alone cuts search error by {pick_cut}% ({num(rt['kcal_mae'])} to {num(hp['kcal_mae'])}), and the cross-check against "
           f"the model's own estimate takes it to {num(h['kcal_mae'])}, while every reported number still comes from a federal food record.")
headline = (f"On {r['n_products']} real Swiss products it is more accurate than both text matching ({cut}% less energy error) and "
            f"Apertus guessing alone ({hold_cut}% less on a held-out half), and every number it reports traces to a federal food record.")
off_line = (f"Running the same energy check over all {off['checked']:,} Swiss products on Open Food Facts flagged "
            f"{off['flagged']:,} ({pct(off['share'])}) whose printed calories contradict their own macronutrients; "
            f"{off['looks_like_kj_typed_as_kcal']} look like kilojoules typed as kilocalories. The list is in `eval/off_energy_flags.csv`.")
glance = (f"**At a glance.** {r['n_products']} real Swiss products, label hidden, receipt-style line in. Bon·Appétit is off by more than "
          f"100 kcal per 100 g on {pct(h.get('over100_kcal'))} of them; plain text matching on {pct(f.get('over100_kcal'))}. Its typical error "
          f"is {num(h['kcal_mae'])} kcal per 100 g, against {num(a['kcal_mae'])} for Apertus guessing with no source and {num(f['kcal_mae'])} "
          f"for text matching. It leaves {pct(h['abstain'])} of lines for you to confirm instead of guessing. The receipt lines are produced "
          f"from real product names by rules we wrote (docs/receipt_rules.md), so real tills may differ.\n\n")
results_md = glance + (f"{r['n_products']} real Swiss products from Open Food Facts, label hidden, receipt-style line in, compared with the printed "
              f"label ({r.get('notes', '')}).\n\n{table}\n\n{off_line}\n\n**Household view.** Over 200 simulated weekly baskets of 20 products, the food-pyramid shares are off by "
              f"{hh['checked']['share_error_pp']} percentage points per group on average, against {hh['fuzzy']['share_error_pp']} for text "
              f"matching. Errors on single products partly cancel over a week, so the gap is smaller here than per product.\n\nThe ceiling row is the best any link to a generic FSVO "
              f"food can do; the gap between it and the hybrid is linking error, which is where the next work goes.")
lesson = (f"Apertus alone produced plausible numbers ({num(a['kcal_mae'])} kcal mean error) with no source. Used as a cross-check on "
          f"its own pick instead of as the answer, the same estimate made the linked results better than either alone ({num(h['kcal_mae'])}).")

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
    s = (s.replace("{{RESULTS}}", results_md).replace("{{RESULTS_TABLE}}", table + "\n\n" + off_line + f"\n\n**Household view.** Over 200 simulated weekly baskets of 20 products, pyramid shares are off by {hh['checked']['share_error_pp']} percentage points per group (text matching {hh['fuzzy']['share_error_pp']}).")
          .replace("{{BY_LANG}}", by_lang).replace("{{N}}", str(r["n_products"])).replace("{{SUMMARY_RESULT}}", summary)
          .replace("{{HEADLINE}}", headline).replace("{{LESSON_NUMBERS}}", lesson).replace("{{COST}}", cost)
          .replace("{{GGUF_SHA}}", "a037df8d87ff6caacee794ee85f55342f2152e0d359b7389033300c3bee5f299"))
    p.write_text(s)
print("filled", headline)
