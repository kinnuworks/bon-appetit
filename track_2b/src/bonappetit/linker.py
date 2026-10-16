"""Link one receipt line to one food, or abstain.

Two Apertus calls per line, both constrained to a JSON schema and with thinking off:
1. Read: write out the shorthand, name the language, say whether it is food, and give a
   generic German food name of the kind used in the FSVO table.
2. Pick: choose one of the retrieved candidates by its list number, or none, and say how sure.
The food layer can then veto the pick. Apertus never writes a nutrient value.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .catalog import Catalog, Candidate
from .foodlayer import check_energy, check_pack, check_unit, helvetism_hints
from .llm import Apertus
from .receipt import Line

READ_SCHEMA = {
    "type": "object",
    "properties": {
        "english": {"type": "string"},
        "german_food_name": {"type": "string"},
        "language": {"type": "string", "enum": ["de", "fr", "it", "en", "unknown"]},
        "is_food": {"type": "boolean"},
    },
    "required": ["english", "german_food_name", "language", "is_food"],
    "additionalProperties": False,
}

PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {"type": "integer"},
        "sure": {"type": "boolean"},
    },
    "required": ["choice", "sure"],
    "additionalProperties": False,
}

READ_SYSTEM = (  # kept short: every output token costs about 0.12 s on a laptop
    "You read lines from Swiss supermarket receipts (Migros, Coop, Denner, Aldi, Lidl, Volg). "
    "Lines are short, upper case, truncated and may be German, French or Italian. They use shop brands "
    "such as M-Budget (M-BUDG), M-Classic, Prix Garantie (PRIX GAR.), Qualité & Prix (QP), Naturaplan, "
    "Betty Bossi, Anna's Best, Sélection, Bio. Write out the shorthand, say which language it is in, "
    "Reply in JSON with: english (the product in a few plain English words), german_food_name (the generic "
    "German food-table name, e.g. 'Vollmilch, UHT', 'Gruyère', 'Teigwaren, roh', 'Karotte, roh'), language "
    "(de, fr, it or en) and is_food (false for bags, deposits, cleaning products and toiletries)."
)

PICK_SYSTEM = (
    "You match a Swiss receipt line to a list of foods from the Swiss Food Composition Database. "
    "Reply in JSON: choice is the number of the entry that best describes the product as bought "
    "(raw unless the line says cooked or ready-made), or 0 if none fits; sure is false when two entries "
    "fit about equally well."
)


@dataclass
class Link:
    line: dict
    read: dict | None = None
    candidates: list[dict] = field(default_factory=list)
    choice: dict | None = None
    status: str = "linked"  # linked | review | nonfood | vetoed
    confidence: str | None = None
    question: str | None = None
    veto: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Linker:
    def __init__(self, catalog: Catalog, llm: Apertus, k: int = 8):
        self.catalog, self.llm, self.k = catalog, llm, k

    def read(self, line: Line) -> dict:
        shop = f" (shop: {line.shop})" if line.shop else ""
        return self.llm.json(
            [{"role": "system", "content": READ_SYSTEM},
             {"role": "user", "content": f"Receipt line{shop}: {line.text}"}],
            READ_SCHEMA,
        )

    def pick(self, line: Line, read: dict, cands: list[Candidate]) -> dict:
        listing = "\n".join(f"{i + 1}. {c.name} [{c.category}]" for i, c in enumerate(cands))
        hints = helvetism_hints(line.text)
        note = f"\nSwiss word note: {'; '.join(hints)}." if hints else ""
        msg = f"Receipt line: {line.text} ({read.get('english', '')}){note}\n{listing}"
        return self.llm.json([{"role": "system", "content": PICK_SYSTEM}, {"role": "user", "content": msg}], PICK_SCHEMA)

    def link(self, line: Line) -> Link:
        out = Link(line=line.to_dict())
        read = self.read(line)
        out.read = read
        # bags, deposits and cleaning products are set aside by rule, whatever the model says
        if line.nonfood_hint or not read.get("is_food", True):
            out.status = "nonfood"
            return out
        hints = helvetism_hints(line.text)
        cands = self.catalog.search([*hints, read.get("german_food_name", ""), read.get("english", ""), line.text], k=self.k)
        out.candidates = [asdict(c) for c in cands]
        if not cands:
            out.status = "review"
            return out
        pick = self.pick(line, read, cands)
        out.confidence = "high" if pick.get("sure") else "low"
        idx = int(pick.get("choice") or 0)
        if not 1 <= idx <= len(cands):
            out.status = "review"
            out.question = f"What is '{line.text}'? It reads like {read.get('english') or 'an unknown product'}."
            return out
        c = cands[idx - 1]
        for verdict in (check_unit(line.pack_is_volume, c.liquid, c.group), check_pack(line.pack_grams, c.group)):
            if not verdict.ok:
                out.status = "vetoed"
                out.veto = {"rule": verdict.rule, "detail": verdict.detail, "candidate": c.name}
                # fall back to the best-ranked candidate that passes the checks
                for alt in cands:
                    if check_unit(line.pack_is_volume, alt.liquid, alt.group).ok:
                        c = alt
                        out.status = "linked"
                        break
                break
        energy = check_energy(self.catalog.nutrients(c.fsvo_id))
        if not energy.ok:  # a food whose own record is inconsistent is never used silently
            out.status = "review"
            out.veto = {"rule": energy.rule, "detail": energy.detail, "candidate": c.name}
        if out.veto and out.status == "linked":
            out.veto["overruled"] = True  # the model's pick was replaced by one that passes the checks
        out.choice = asdict(c)
        # The 8B model almost never says it is sure, so "sure" is reported, not obeyed. A line goes
        # to review when it answered 0 above, or when the food layer had to overrule it.
        if out.veto and out.status != "linked":
            out.status = "review"
            runner = next((x for x in cands if x.fsvo_id != c.fsvo_id), None)
            out.question = f"'{line.text}': {c.name}" + (f" or {runner.name}?" if runner else "?")
        return out
