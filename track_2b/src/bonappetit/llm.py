"""A small OpenAI-compatible client for Apertus, with a replay cache.

Configuration follows the Hack Apertus template:
  LLM_NAME      model name, e.g. hf.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF (local) or swiss-ai/apertus-v1.5-70b
  LLM_BASE_URL  endpoint, e.g. http://localhost:11434/v1 (Ollama) or a Swiss cloud endpoint
  LLM_API_KEY   key for hosted endpoints; any string for a local server

Every request and response is stored in a JSONL cache keyed by a hash of the request.
With BONAPPETIT_REPLAY=1 the client answers only from the cache, which makes the
evaluation reproducible without a model.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import httpx

DEFAULT_MODEL = "hf.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF"
DEFAULT_URL = "http://localhost:11434/v1"


class ReplayMiss(RuntimeError):
    pass


class Apertus:
    def __init__(self, cache_path: str | Path | None = None):
        self.model = os.environ.get("LLM_NAME", DEFAULT_MODEL)
        self.base_url = os.environ.get("LLM_BASE_URL", DEFAULT_URL).rstrip("/")
        self.api_key = os.environ.get("LLM_API_KEY", "local")
        self.replay = os.environ.get("BONAPPETIT_REPLAY") == "1"
        root = Path(__file__).resolve().parents[2]
        self.cache_path = Path(cache_path or os.environ.get("BONAPPETIT_CACHE", root / "data" / "llm_cache.jsonl"))
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._cache[rec["key"]] = rec
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.seconds = 0.0

    def _key(self, messages, schema) -> str:
        blob = json.dumps({"model": self.model, "messages": messages, "schema": schema}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def json(self, messages: list[dict], schema: dict, max_tokens: int = 300) -> dict:
        key = self._key(messages, schema)
        if key in self._cache:
            return self._cache[key]["response"]
        if self.replay:
            raise ReplayMiss(key)
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "seed": 0,
            "max_tokens": max_tokens,
            # Plain JSON mode: on llama.cpp a full schema grammar was 4x slower and made the 8B model
            # answer "none" far more often. The schema is still enforced below, in code.
            "response_format": {"type": "json_object"},
        }
        t = time.time()
        r = httpx.post(f"{self.base_url}/chat/completions", json=body,
                       headers={"Authorization": f"Bearer {self.api_key}"}, timeout=180)
        r.raise_for_status()
        data = r.json()
        dt = time.time() - t
        text = data["choices"][0]["message"]["content"]
        try:
            out = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            out = json.loads(text[start : end + 1]) if start >= 0 else {}
        out = conform(out, schema)
        usage = data.get("usage") or {}
        rec = {"key": key, "model": self.model, "response": out, "seconds": round(dt, 3),
               "tokens_in": usage.get("prompt_tokens"), "tokens_out": usage.get("completion_tokens")}
        with self._lock:
            self._cache[key] = rec
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.calls += 1
            self.tokens_in += usage.get("prompt_tokens") or 0
            self.tokens_out += usage.get("completion_tokens") or 0
            self.seconds += dt
        return out


def conform(obj: dict, schema: dict) -> dict:
    """Coerce a model answer to the schema: keep known keys, fill missing ones, fix simple types."""
    props = schema.get("properties", {})
    out = {}
    for k, spec in props.items():
        v = obj.get(k) if isinstance(obj, dict) else None
        t = spec.get("type")
        if t == "integer":
            try:
                v = int(str(v).strip().split()[0]) if v is not None else 0
            except (ValueError, IndexError):
                v = 0
        elif t == "number":
            try:
                v = float(str(v).replace(",", ".").split()[0]) if v is not None else None
            except (ValueError, IndexError):
                v = None
        elif t == "boolean":
            v = v if isinstance(v, bool) else str(v).lower() in {"true", "yes", "1"}
        else:
            v = "" if v is None else str(v)
            if "enum" in spec and v not in spec["enum"]:
                v = spec["enum"][-1]
        out[k] = v
    return out
