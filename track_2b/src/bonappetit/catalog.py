"""Food catalogue and candidate search.

The catalogue is the FSVO Swiss Food Composition Database (generic foods and a few
brand products). Search combines lexical matching with optional Swiss multilingual
embeddings (andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir, an Apertus-derived
model), so French and Italian receipt lines can reach German food names.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from .foodlayer import group_for

DATA = Path(os.environ.get("BONAPPETIT_DATA", Path(__file__).resolve().parents[2] / "data"))
NUTRIENTS = ["energy_kcal", "fat", "saturated_fat", "carbohydrates", "sugars", "fiber", "proteins", "salt"]
EMBED_MODEL = "andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir"


def norm(s: str) -> str:
    s = str(s).lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


@dataclass
class Candidate:
    fsvo_id: int
    name: str
    category: str
    group: str
    liquid: bool
    score: float

    def short(self) -> str:
        return f"{self.fsvo_id}: {self.name} [{self.category}]"


class Catalog:
    def __init__(self, path: Path | None = None, use_embeddings: bool | None = None):
        self.df = pd.read_csv(path or DATA / "fsvo.csv")
        self.df["group"] = self.df["category"].map(group_for)
        self.df["search"] = (self.df["name"].fillna("") + " " + self.df["synonyms"].fillna("")).map(norm)
        self.by_id = self.df.set_index("fsvo_id")
        if use_embeddings is None:
            use_embeddings = os.environ.get("BONAPPETIT_EMBED", "1") == "1"
        self._emb = None
        self._doc_vecs = None
        if use_embeddings:
            self._load_embeddings()

    def _load_embeddings(self) -> None:
        cache = DATA / "fsvo_embeddings.npy"
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return
        try:
            self._emb = SentenceTransformer(EMBED_MODEL, device=os.environ.get("BONAPPETIT_DEVICE", "cpu"))
        except Exception:  # offline without a cached model: lexical search only
            self._emb = None
            return
        if cache.exists():
            vecs = np.load(cache)
            if len(vecs) == len(self.df):
                self._doc_vecs = vecs
                return
        docs = (self.df["name"].fillna("") + ". " + self.df["category"].fillna("")).tolist()
        self._doc_vecs = self._emb.encode_document(docs, truncate_dim=256, normalize_embeddings=True, batch_size=64)
        np.save(cache, self._doc_vecs)

    @property
    def has_embeddings(self) -> bool:
        return self._doc_vecs is not None

    def row(self, fsvo_id: int) -> pd.Series:
        return self.by_id.loc[int(fsvo_id)]

    def nutrients(self, fsvo_id: int) -> dict:
        r = self.row(fsvo_id)
        return {k: (None if pd.isna(r[k]) else float(r[k])) for k in NUTRIENTS}

    def _cand(self, idx: int, score: float) -> Candidate:
        r = self.df.iloc[idx]
        return Candidate(int(r.fsvo_id), r["name"], r["category"], r["group"], bool(r["liquid"]), float(score))

    def lexical(self, query: str, k: int = 8) -> list[Candidate]:
        hits = process.extract(norm(query), self.df["search"].tolist(), scorer=fuzz.token_set_ratio, limit=k)
        return [self._cand(i, s / 100) for _, s, i in hits]

    def semantic(self, query: str, k: int = 8) -> list[Candidate]:
        if not self.has_embeddings:
            return []
        q = self._emb.encode_query([query], truncate_dim=256, normalize_embeddings=True)[0]
        sims = self._doc_vecs @ q
        top = np.argsort(-sims)[:k]
        return [self._cand(int(i), float(sims[i])) for i in top]

    def search(self, queries: list[str], k: int = 10) -> list[Candidate]:
        """Reciprocal-rank fusion over lexical and semantic hits for several query strings."""
        scores: dict[int, float] = {}
        keep: dict[int, Candidate] = {}
        for q in [q for q in queries if q]:
            for ranked in (self.lexical(q, k), self.semantic(q, k)):
                for rank, c in enumerate(ranked):
                    scores[c.fsvo_id] = scores.get(c.fsvo_id, 0) + 1 / (60 + rank)
                    keep.setdefault(c.fsvo_id, c)
        best = sorted(scores, key=scores.get, reverse=True)[:k]
        return [keep[i] for i in best]


@lru_cache(maxsize=1)
def default_catalog() -> Catalog:
    return Catalog()
