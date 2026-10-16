# Data and licences

| File | Content | Licence |
|---|---|---|
| `data/fsvo.csv` | Swiss Food Composition Database V6.5 (27.06.2023, corrected 17.08.2023) as one table | Free reuse with attribution. Source: Swiss Food Composition Database, Federal Food Safety and Veterinary Office (FSVO), naehrwertdaten.ch |
| `data/fsvo_embeddings.npy` | Embeddings of the FSVO names, made with andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir | Derived from the FSVO table; same attribution |
| `eval/gold.jsonl` | 160 Open Food Facts products: barcode, name, brand, quantity, printed nutrition values, our receipt-style line | Contains information from Open Food Facts, made available under the Open Database Licence (ODbL 1.0). Individual contents under the Database Contents Licence (DbCL). Each row carries a `licence` field. |
| `eval/off_energy_flags.csv` | Swiss Open Food Facts products whose printed energy fails the energy check | ODbL 1.0, as above |
| `eval/predictions.jsonl`, `eval/results.json`, `data/llm_cache.jsonl`, `eval/llm_cache.jsonl` | Our model outputs and scores | CC-BY-4.0 |
| Code | `src/`, `eval/*.py`, `scripts/`, `tests/`, `site/` | Apache-2.0 |
| Documentation | `*.md`, `docs/` | CC-BY-4.0 |

The ODbL files are kept under ODbL, as share-alike requires. They are not relicensed under Apache-2.0 or CDLA-Permissive-2.0. CDLA-Permissive-2.0 is the licence offered for donated receipts in `docs/consent_template.md`; none have been collected yet.

No personal data is used. The receipt parser keeps only article lines, quantities and prices, and the local app stores nothing.
| `eval/off_corrections_kj_as_kcal.csv` | The 433 likely kilojoule-as-kilocalorie entries with product links | ODbL 1.0, as above |
