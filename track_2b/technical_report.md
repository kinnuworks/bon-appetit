# Technical report: Bon·Appétit

Swiss supermarket receipts are unreadable to software: lines are truncated, multilingual and coded, and the Migros export has no barcodes. Bon·Appétit uses Apertus v1.5 8B, running on the household's own laptop, to read each line and link it to the federal Swiss Food Composition Database, with a symbolic food layer that checks every pick and code that does every number. On 160 real Swiss products it cuts the energy error of text matching by 28%, nearly doubles the share of products put in the right food group, and every number it reports traces to a federal food record.

- **Track:** Track 2B: Bon·Appétit
- **Event:** Online
- **Team:** Dhiraj Kavuri (solo)
- **Demo:** [video link] · live page https://kinnuworks.github.io/bon-appetit/
- **Code:** https://github.com/kinnuworks/bon-appetit

## 1. Summary

Households, dietitians and prevention programmes already hold a detailed record of what people eat: their supermarket receipts. They cannot use it, because a line such as `QP GRUY.RAPE 200G` means nothing to a lookup table, and the purchase history is too sensitive to send to a foreign cloud model. Bon·Appétit reads receipts with Apertus on the household's own computer, links each line to the FSVO database, abstains when unsure, and turns a week of shopping into grams per adult per day for each group of the Swiss food pyramid. On 160 real Swiss products with printed nutrition labels, the hybrid's energy estimate is off by 123 kcal per 100 g on average, 28% less than fuzzy text matching (171), and it names the right food group for 49% of products against 27%. Apertus's pick is what does it: search alone, without the pick, is off by 153, so the pick cuts the error by 19%. Apertus guessing the numbers itself lands close (122) but gives no source that anyone could check or correct.

## 2. Architecture

```
receipt (CSV, PDF, text, photo) ─► parser (rules) ─► Apertus: read line ─► search (lexical + Swiss embeddings)
   ─► Apertus: pick or abstain ─► food layer (unit, energy, pack, Swiss words) ─► ledger (code) ─► Apertus: one nudge (slots)
```

| Component | What it does | Where it runs |
|---|---|---|
| Parser | Prices, quantities, pack sizes, multipacks, non-food hints | Python, rules |
| Read | One Apertus call: English description, language, food or not, generic German food name | Apertus v1.5 8B |
| Search | Reciprocal-rank fusion of token-set matching and an Apertus-derived Swiss embedding model over 1,145 FSVO foods | CPU or Apple GPU |
| Pick | One Apertus call: list number of the best candidate, or 0 | Apertus v1.5 8B |
| Food layer | Vetoes physically impossible links; Swiss food-word glossary; SGE food groups | Python, rules |
| Ledger | Grams per adult per day, sugar, salt, saturated fat, against SGE-derived references | Python |
| Nudge | One sentence in DE/FR/IT/EN; numbers enter only as placeholders filled by code | Apertus v1.5 8B |

### Target architecture

**b) Air-gapped**, also **a) on-premise**. `make airgap` runs the app and a llama.cpp server on a Docker network marked `internal`, and the app runs an egress test before it starts (it tries four outside hosts and refuses to start if any answers). Build time needs the internet once: Docker images, the GGUF model file, the embedding model, the Open Food Facts dump for evaluation. Runtime needs none. A Swiss cloud endpoint works through `LLM_BASE_URL` (option c).

## 3. Use of Apertus

- **Model:** `swiss-ai/Apertus-v1.5-8B`, as the community text-only Q4_K_M GGUF `Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF`. The text-only conversion follows the FHNW conversion that organisers accepted on Discord for Track 2B.
- **How it is used:** inference, two calls per receipt line plus one per nudge; thinking off; temperature 0; seed 0; JSON output.
- **Where it runs:** local weights through Ollama 0.40 (Apple M5, 16 GB) for development and evaluation; llama.cpp server in Docker for `make local` and `make airgap`.
- **Other open models:** `andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir` (Apache-2.0), an embedding model derived from Apertus, for candidate search. No closed model is used at runtime or in evaluation.

Two choices came from measurement. A full JSON-schema grammar on llama.cpp made each call about four times slower and made the 8B model answer "no match" for almost every line, including easy ones such as bananas; plain JSON mode with the schema enforced in code fixed both. The model also reports "not sure" for nearly every pick, so that flag is recorded but does not decide anything; abstention comes from choosing 0, and review from the food layer.

## 4. Data

| Source | Use | Licence |
|---|---|---|
| FSVO Swiss Food Composition Database V6.5 (1,109 generic foods, 36 brand products) | The food catalogue and every nutrient number | Free reuse with attribution |
| Open Food Facts product database (parquet dump, October 2026) | Evaluation: Swiss products with printed nutrition values | ODbL-1.0; barcodes and label values for the 160 evaluation products are kept under ODbL, the dump is not redistributed |
| SGE Swiss food pyramid portions | Daily reference amounts per food group | Cited guidance |

No personal data is used. No real receipts were available under a licence, so receipt lines in the evaluation are produced from real product names by documented rules (`eval/build_set.py`): shop-brand shorthand (M-Budget becomes `M-BUDG`, Qualité & Prix becomes `QP`), accent folding, upper case, long words cut to seven letters plus a dot, 24 characters, pack size appended.

## 5. Evaluation

**Task.** For each product, hide the printed label, give the system only the receipt-style line, and compare its per-100 g estimate with the printed values. A method that links to an FSVO food is scored with that food's values.

**Set.** 160 products were sampled with seed 42 from the 74,192 Open Food Facts entries sold in Switzerland with complete nutrition tables (80 German, 50 French, 30 Italian names). The model runs at about 8 tokens per second on the laptop, so the run was stopped at the deadline after 160 products. Languages were interleaved in the run order, so the scored products keep the same language mix. The glossary and shortening rules were written before this set was built.

**Methods.**
1. Fuzzy text match: the best token-set match among FSVO names, the approach of earlier receipt tools.
2. Swiss embeddings only: nearest FSVO food by embedding.
3. Search only (ablation): the top candidate of the hybrid's own search, with no Apertus pick. The difference to the hybrid is what the pick step adds.
4. Apertus alone: the model estimates the nutrients directly from the line, with no database and no source.
5. Bon·Appétit hybrid.
6. Label-informed ceiling: the FSVO food closest to the printed label, chosen by looking at the label. No real system can do this; it shows how close any link to generic FSVO foods could get.

The hybrid abstains on a few lines; the second table compares every method on exactly the products the hybrid answered.

| Method | kcal error per 100 g (95% CI) | Off by >100 kcal | Sugar error, g | Salt error, g | Food group right | Abstains |
|---|---|---|---|---|---|---|
| Fuzzy text match | 171 (151 to 195) | 54% | 13.6 | 0.85 | 27% | 0% |
| Swiss embeddings only | 194 (171 to 219) | 62% | 17.9 | 0.85 | 27% | 0% |
| Search only, no Apertus pick (ablation) | 153 (129 to 177) | 49% | 12.3 | 0.92 | 38% | 5% |
| Apertus alone, guessing (no source) | 122 (104 to 144) | 44% | 10.3 | 0.69 | n/a | 6% |
| Bon·Appétit hybrid | 123 (102 to 145) | 39% | 10.7 | 0.69 | 49% | 8% |
| Label-informed ceiling (best FSVO food) | 12 (10 to 15) | 0% | 1.2 | 0.66 | 61% | 0% |

| Method, on the products the hybrid answered | n | kcal error (95% CI) | Off by >100 kcal |
|---|---|---|---|
| Fuzzy text match | 148 | 172 (149 to 197) | 53% |
| Swiss embeddings only | 148 | 196 (170 to 221) | 62% |
| Search only, no Apertus pick (ablation) | 148 | 153 (129 to 176) | 50% |
| Apertus alone, guessing (no source) | 140 | 116 (98 to 137) | 41% |
| Bon·Appétit hybrid | 148 | 123 (102 to 145) | 39% |
| Label-informed ceiling (best FSVO food) | 148 | 12 (10 to 15) | 0% |

Running the same energy check over all 86,517 Swiss products on Open Food Facts flagged 3,035 (4%) whose printed calories contradict their own macronutrients; 433 look like kilojoules typed as kilocalories. The list is in `eval/off_energy_flags.csv`.

**Household view.** Over 200 simulated weekly baskets of 20 products, the food-pyramid shares the hybrid reports are off by 8.4 percentage points per group on average, against 8.5 for fuzzy matching and 8.9 for search alone. Errors on single products partly cancel out over a week, which is what a household sees.

**By language.** The Italian sample is small, so its numbers carry wide uncertainty.

| Language | n | Fuzzy kcal error | Embeddings kcal error | Apertus alone kcal error | Hybrid kcal error | Hybrid food group right |
|---|---|---|---|---|---|---|
| DE | 80 | 164 | 216 | 123 | 124 | 56% |
| FR | 50 | 183 | 179 | 112 | 106 | 48% |
| IT | 30 | 170 | 161 | 137 | 157 | 31% |

**Reproduce.** `make eval` re-scores the stored predictions without a model and checks the SHA-256 of the results against `eval/results.sha256`. `python -m eval.run` regenerates the predictions with any Apertus endpoint; every model answer is also stored in `data/llm_cache.jsonl`.

## 6. Value and cost

Measured on an Apple M5 laptop with 16 GB, Apertus v1.5 8B Q4_K_M through Ollama, four requests in parallel: 47.1 seconds per receipt line for both calls together, including queueing. A weekly receipt of 20 food lines therefore takes about 15.7 minutes on one laptop, with no subscription and no per-request fee. Electricity for 1,000 such receipts is about CHF 2.36 (laptop at 30 W, 20 food lines per receipt, CHF 0.30 per kWh, measured seconds per line with 4 parallel requests). A server GPU or a Swiss cloud endpoint serving the 8B model is many times faster; that is the path for a retailer-scale service.

The users are households first, then dietitians, home-care services and prevention programmes working with a client's consent, and retailers who want a nutrition view inside a loyalty app without sending purchase data to a foreign model. A first pilot needs 20 consenting households, four weeks of receipts, a dietitian's review of the reference amounts, and one outcome read from the receipts themselves: the change in the vegetables-and-fruit share. The FoodCoach trial (NCT05597969) is the reference design. No effect is claimed yet.

## 7. Limitations

- Purchases are not intake: waste, guests and meals out are invisible. The output is a household trend by food group, not a per-person diet record.
- The receipt lines are synthetic, built from real names by stated rules. Real tills cut and code differently; the review queue and a household alias list are meant to absorb this.
- FSVO has generic foods, so a branded product is scored against a generic value. The oracle row shows how much error that alone causes.
- One run, one seed, one quantisation. 70B was not evaluated because hackathon inference keys were exhausted.
- Photo receipts are not supported yet; Apertus image input was not used, because the community GGUF builds are text-only.
- Reference amounts per food group are derived by hand from SGE portions and are illustrative until a dietitian reviews them. Lines without a pack size get a default amount per group, counted as estimated.
- The evaluation ran before two small changes to the linker (non-food words now always win, and the energy check is applied to the chosen FSVO food). Neither applies to the evaluation products, which are all foods with consistent FSVO records.

## 8. Lessons on building with Apertus 1.5

- The 8B model reads shop shorthand well (`M-BUDG VOLLMILCH UHT 1L` becomes "M-Budget whole milk, UHT, 1 litre") but misses Swiss food words: it read `RUEBLI` (carrot) as kale and as flatbread. A twenty-line glossary in the food layer fixed it; the words belong in localisation data for the next Apertus release.
- Asked for Swiss spelling, the 8B model still wrote "ß" in German suggestions ("Süßigkeiten"). Code now converts it, as Swiss orthography always uses "ss".
- Without the target language's food-group names in the prompt, it mixed English group names into German and French text, and once called a household "doing great with sweets" at five times the guide. Giving it the direction ("too little", "too much") and the names in the target language fixed both.
- Constrained decoding with a full schema hurt accuracy as well as speed on llama.cpp.
- The model is cautious when it chooses from a list and almost never says it is sure. Selection by list number plus external checks worked better than asking for confidence.
- Apertus alone produced plausible numbers for every product (122 kcal mean error) but cannot say where they came from. In the hybrid it never writes a number, so every value in the household report can be checked.

## 9. Next steps

Real receipts donated with consent (a consent template is in `docs/`); Coop Supercard export; a household alias memory shared across weeks; the 70B model for the read step on a Swiss cloud; reporting nutrient ranges instead of point values; a contribution back to Open Food Facts listing Swiss entries whose printed values fail the Atwater check.

## License

Creative Commons Attribution 4.0 (CC-BY-4.0). All Hack Apertus projects are open-sourced. Code: Apache-2.0.

## References

- FSVO, Swiss Food Composition Database V6.5, naehrwertdaten.ch, 2023.
- Swiss Society for Nutrition (SGE), Swiss food pyramid, sge-ssn.ch.
- Open Food Facts, product database, ODbL.
- Apertus v1.5 model card, huggingface.co/swiss-ai/Apertus-v1.5-8B.
- A. Martin, apertus-v1.1-swiss-embed-0.4b-bidir, Hugging Face.
- FoodCoach trial, ClinicalTrials.gov NCT05597969; Receipt2Nutrition, ETH Zurich.
- TooSweet, Open Food Hackdays 2018, hack.opendata.ch/project/153.
