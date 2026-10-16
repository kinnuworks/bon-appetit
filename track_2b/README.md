# Bon·Appétit

Bon·Appétit reads Swiss supermarket receipts and shows a household what it actually eats, measured against the Swiss food pyramid. It runs on the household's own computer. Apertus v1.5 reads the receipt shorthand, a federal food database supplies the numbers, and nothing leaves the machine.

**Hack Apertus 2026 · Track 2B (own project) · Online** · Website and live demo: https://kinnuworks.github.io/bon-appetit/ · Technical report: [technical_report.md](technical_report.md) ([PDF](DhirajKavuri_Report.pdf)) · Demo video: {{VIDEO}}

## The problem

A Swiss till receipt says `M-BUDG VOLLMILCH UHT 1L`, `QP GRUY.RAPE 200G` or `NATURAPLAN BIO RUEBLI 1KG`. Lines are cut short, mix German, French and Italian, and use shop-brand codes. The Migros Cumulus export has no barcodes, and Coop only gives PDFs. A lookup table or fuzzy text match cannot turn these lines into food, so households, dietitians and prevention programmes cannot use the purchase data they already have.

Purchase histories also reveal health conditions, religion and money. Under the revised Swiss data protection act, health data is sensitive personal data, so this is a job for a model that runs where the data is.

## What it does

1. **Reads the receipt.** Migros Cumulus CSV, Coop PDF, pasted text, or a photo through local OCR. Prices, quantities, pack sizes (`6X1.5L` becomes 9 litres) and non-food lines are handled by rules, not by the model.
2. **Writes out each line with Apertus.** One call per line returns a plain description, the language, whether it is food, and a generic German food-table name.
3. **Finds candidates.** Lexical search plus Swiss multilingual embeddings derived from Apertus ([andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir](https://huggingface.co/andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir)) search the 1,145 foods of the [FSVO Swiss Food Composition Database](https://naehrwertdaten.ch). French and Italian lines reach German food names this way.
4. **Picks or abstains with Apertus.** A second call chooses one candidate by its list number, or none. A line with no good match goes to a review queue with a question.
5. **Checks the pick in code.** The food layer rejects picks that break physical rules: a line sold in litres cannot be a solid cheese, energy must agree with macronutrients (Atwater), and pack sizes must be household sizes. A small glossary of Swiss food words (Rüebli, Nüsslisalat, Peperoni) covers words the model misreads.
6. **Adds it up.** Code computes grams per adult per day for each group of the Swiss food pyramid, plus sugar, salt and saturated fat, and compares them with reference amounts derived from the Swiss Society for Nutrition portions.
7. **Suggests one swap**, in German, French, Italian or English. Apertus writes the sentence; numbers enter only through placeholders that code fills, so the model cannot change them.

Apertus never writes a nutrient value.

## Results

{{RESULTS}}

## Run it

From the repository root:

```bash
make run      # builds the app image, re-scores the stored evaluation, then serves http://localhost:8080
```

`make run` reaches the model through the template variables, so a judge can point it at any Apertus server:

```bash
export LLM_NAME=swiss-ai/apertus-v1.5-8b   # or the 70B, or the local GGUF name
export LLM_BASE_URL=https://your-endpoint/v1
export LLM_API_KEY=...
make run
```

Other targets:

| Target | What it does |
|---|---|
| `make local` | App plus a bundled llama.cpp server with Apertus v1.5 8B (Q4_K_M GGUF, CPU). Downloads the model file once. |
| `make airgap` | The same two containers on a Docker network with no route outside. The app first runs an egress test and refuses to start if any outside host answers. |
| `make eval` | Re-scores the stored predictions without a model and checks the result hash in `eval/results.sha256`. |
| `make test` | Unit tests. |

## Deployment target

**b) Air-gapped**, and **a) on-premise**. The model, the food database and the app run on one machine. Build time needs the internet once (Docker images, the model file, the embedding model); runtime needs none. A Swiss cloud endpoint (c) works through `LLM_BASE_URL` for organisations that prefer it.

## Repository

| Path | What it is |
|---|---|
| `src/bonappetit/` | The package: receipt parser, catalogue search, food layer, Apertus client with replay cache, linker, ledger, local server, egress test |
| `eval/` | Evaluation set builder, runner, scorer, stored predictions and results |
| `data/fsvo.csv` | The FSVO database as one tidy table (1,145 foods) |
| `data/llm_cache.jsonl` | Every Apertus request and answer from the evaluation, for replay |
| `site/` | The website and in-browser demo |
| `scripts/` | Data and model download, demo builder |
| `tests/` | Unit tests |
| `technical_report.md` | Architecture, evaluation, limits, lessons on Apertus |

## Data and licences

Code: Apache-2.0. Documentation: CC-BY-4.0. FSVO Swiss Food Composition Database V6.5: free reuse with attribution (Federal Food Safety and Veterinary Office). Open Food Facts: ODbL-1.0; the evaluation set keeps barcodes and label values for 160 products under ODbL, and the full dump is downloaded at build time, never redistributed. No personal data is used anywhere.

## Prior work

TooSweet (Open Food Hackdays 2018) ranked Migros Cumulus purchases by sugar. ETH Zurich's FoodCoach trial (NCT05597969) and Receipt2Nutrition studied nutrition from digital receipts. Bon·Appétit adds multilingual reading of raw receipt lines with an open Swiss model, abstention, a symbolic check, and an evaluation against printed labels that anyone can re-run.

## Not medical advice

Bon·Appétit describes purchases, not what each person eats, and refers to the Swiss dietary recommendations. It does not diagnose or treat anything.

---

<details><summary>Track 2B brief from the Hack Apertus template</summary>

# Track 2 B: Own Project

Bring your own idea and build a working Apertus prototype that tackles a problem you care about — any domain, any use case. The project must be new, started within the hackathon period.

Submissions must use the Apertus model family.
For Track 2 this means that submitted solutions must be built with Apertus. Other open-weights models can be used to support development, e.g. as automatic judges during evaluation. Their role must be clearly described in the submission report.

💬 In case you have questions, join the conversation on [Discord](https://discord.gg/hack-apertus) or send an email to “hello@hackapertus.ch”

---

## 🔧 Resources & Tools

Check our resources & tools page for detailed information:
https://hackapertus.notion.site/resources-tools

| Models           | URL                                      |
|------------------|------------------------------------------|
| Apertus v1.5 8B  | [huggingface.co/swiss-ai/Apertus-v1.5-8B](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)  |
| Apertus v1.5 70B | [huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) |


## Target architecture (mandatory)

Whatever you build in Track 2B must be deployable in one of these three architectures:

- **a) On-premise** — on the organisation's own infrastructure, under its own administration.
- **b) Air-gapped** — with no external network connection at runtime.
- **c) Sovereign Swiss cloud** — on a cloud platform operated in Switzerland, under Swiss jurisdiction, with Swiss data residency.

---

## Data

The `data/` directory must not exceed 100 MB.

---

## 📦 Submission Requirements & Deliverables

❗️ Submissions are not handled on Devpost but via this URL only:
http://hackapertus.ch/online-hack/submissions

The submission must: 
1. follow the template repo and include all prerequisite files and definitions
2. follow the specified input/output formats
3. run in a Docker container, launched with `make run` from the root of the project
4. run end-to-end when judges try to run it

### Git repo (URL)
- Create your repo from this template (**Use this template**) and work in the `track_2b/` challenge directory. Delete the other track challenge directories.
- Keep `track_2b/` as it is: don't rename it or move its files.
- Set the repo to PUBLIC (Settings --> Collaborators --> Manage Visibility)
- Submit the URL of YOUR Git repo.

### Technical Report (pdf)
- Update [technical_report.md](technical_report.md) in this repository with all the details for your submission.
- Upload a pdf of your technical report to this directory, named as `TeamName_Report.pdf`.
- Format: pdf, max. 6 pages w/o references
- Submit the pdf of the technical report.

### Demo video (URL)
- Max. 2 min demo video of your prototype

### Dataset (URL) - optional, depending on your project
Submitted datasets must comply with our guidelines for responsibly sourced datasets.

- Create a user account on Hugging Face
- Clone our dataset template on Hugging Face: https://huggingface.co/datasets/HackApertus/online_hack_template
- Complete the dataset card with all required information
- Upload your dataset. It should consist of the following components:
    - evaluation dataset (i.e. individual test cases)
    - model response dataset (i.e. the model response to each test case)
    - metadata file (i.e. additional information about each test case; where relevant, this file must contain instance-level licensing information) 
- Make sure your dataset access control is set to PUBLIC
- Provide the URL of _your_ data set


---

## ⚖️ Judging Criteria

1. Purposeful use of AI
2. Technical rigour
3. Value, cost & scalability
4. Sovereign deployability
5. Implementation feasibility

Judges use a Scale 0–5 per dimension.

---

## Support

**Licensing requirements**
Please check our Terms & Conditions (6. What you build is open source):
https://hackapertus.ch/terms-and-conditions

## FAQ
💡 https://hackapertus.ch/faq

## Contact
💬 In case you have questions, join the conversation on Discord or send an email to “hello@hackapertus.ch”

</details>
