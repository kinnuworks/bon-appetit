"""Run every method on the evaluation set and store raw predictions (needs a model, or the replay cache)."""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from bonappetit.catalog import Catalog
from bonappetit.linker import Linker
from bonappetit.llm import Apertus
from bonappetit.receipt import make_line

GOLD = "eval/gold.jsonl"
OUT = "eval/predictions.jsonl"

GUESS_SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "number"} for k in ["energy_kcal", "sugars", "salt", "fat", "proteins", "carbohydrates"]},
    "required": ["energy_kcal", "sugars", "salt", "fat", "proteins", "carbohydrates"],
    "additionalProperties": False,
}


def main(limit: int | None = None):
    items = [json.loads(l) for l in open(GOLD)]
    # interleave languages so that any prefix of the run covers German, French and Italian
    by = {}
    for it in items:
        by.setdefault(it["lang"], []).append(it)
    order = []
    while any(by.values()):
        for lang in ("de", "fr", "de", "it", "fr", "de"):
            if by.get(lang):
                order.append(by[lang].pop(0))
    items = order[:limit]
    cat = Catalog(use_embeddings=True)
    llm = Apertus()
    linker = Linker(cat, llm)

    def one(it):
        line = make_line(it["receipt_line"], shop=None)
        rec = {"barcode": it["barcode"]}
        rec["fuzzy"] = cat.lexical(it["receipt_line"], k=1)[0].fsvo_id
        sem = cat.semantic(it["receipt_line"], k=1)
        rec["embed"] = sem[0].fsvo_id if sem else None
        t = time.time()
        link = linker.link(line)
        rec["hybrid"] = {"status": link.status, "fsvo_id": (link.choice or {}).get("fsvo_id"),
                         "veto": link.veto, "english": (link.read or {}).get("english"),
                         "candidates": [c["fsvo_id"] for c in link.candidates]}
        rec["hybrid_seconds"] = round(time.time() - t, 2)
        guess = llm.json([{"role": "user", "content":
            f"Swiss supermarket receipt line: {it['receipt_line']}. Estimate the nutrition values per 100 g "
            "(energy_kcal, sugars, salt, fat, proteins, carbohydrates in grams). Reply in JSON."}], GUESS_SCHEMA, max_tokens=80)
        rec["apertus_only"] = guess
        return rec

    with ThreadPoolExecutor(int(os.environ.get("BONAPPETIT_WORKERS", "4"))) as ex, open(OUT, "w") as f:
        for i, rec in enumerate(ex.map(one, items)):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if i % 10 == 0:
                print(i, flush=True)
    json.dump({"calls": llm.calls, "tokens_in": llm.tokens_in, "tokens_out": llm.tokens_out,
               "model_seconds": round(llm.seconds, 1), "model": llm.model},
              open("eval/run_stats.json", "w"), indent=2)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
