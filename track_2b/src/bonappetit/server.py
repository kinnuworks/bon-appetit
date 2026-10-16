"""Local web app: serves the site and a small API. Nothing is stored or sent anywhere."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .catalog import default_catalog
from .ledger import summarise
from .linker import Linker
from .llm import Apertus
import tempfile

from .receipt import parse_migros_csv, parse_pdf, parse_text

MAX_UPLOAD = 2_000_000  # bytes; a receipt is far smaller

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Bon·Appétit", docs_url="/api/docs")
_llm = Apertus()


@app.on_event("startup")
def check_model() -> None:
    """Say clearly at startup if the model endpoint cannot be reached."""
    import httpx

    base = getattr(_llm, "base_url", "")
    try:
        httpx.get(f"{base}/models", timeout=5, headers={"Authorization": f"Bearer {getattr(_llm, 'api_key', '')}"})
        print(f"model endpoint reachable: {base}")
    except Exception:
        hint = " Inside Docker, use host.docker.internal instead of localhost." if "localhost" in base or "127.0.0.1" in base else ""
        print(f"WARNING: model endpoint {base} is not reachable.{hint} The site still works; live reading will fail.")


@app.get("/api/health")
def health():
    return {"ok": True, "model": getattr(_llm, "model", None), "endpoint": getattr(_llm, "base_url", None)}


@app.post("/api/analyze")
async def analyze(text: str = Form(""), shop: str = Form(""), adults: float = Form(1.0),
                  file: UploadFile | None = File(None)):
    if file is not None:
        blob = await file.read(MAX_UPLOAD + 1)
        if len(blob) > MAX_UPLOAD:
            return JSONResponse({"error": "file too large"}, status_code=413)
        name = (file.filename or "").lower()
        if name.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                tmp.write(blob)
                tmp.flush()
                lines = parse_pdf(tmp.name, shop or "Coop")
        else:
            raw = blob.decode("utf-8", errors="replace")
            lines = parse_migros_csv(raw) if name.endswith(".csv") else parse_text(raw, shop or None)
    else:
        lines = parse_text(text, shop or None)
    linker = Linker(default_catalog(), _llm)
    links = [linker.link(l).to_dict() for l in lines]
    return JSONResponse({"links": links, "summary": summarise(links, default_catalog(), adults=adults)})


app.mount("/", StaticFiles(directory=os.environ.get("BONAPPETIT_SITE", ROOT / "site"), html=True), name="site")
