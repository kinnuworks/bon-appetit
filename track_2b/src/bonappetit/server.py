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
from .receipt import parse_migros_csv, parse_text

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Bon·Appétit", docs_url="/api/docs")
_llm = Apertus()


@app.get("/api/health")
def health():
    return {"ok": True, "model": _llm.model, "endpoint": _llm.base_url, "replay": _llm.replay}


@app.post("/api/analyze")
async def analyze(text: str = Form(""), shop: str = Form(""), adults: float = Form(1.0),
                  file: UploadFile | None = File(None)):
    if file is not None:
        raw = (await file.read()).decode("utf-8", errors="replace")
        lines = parse_migros_csv(raw) if file.filename.lower().endswith(".csv") else parse_text(raw, shop or None)
    else:
        lines = parse_text(text, shop or None)
    linker = Linker(default_catalog(), _llm)
    links = [linker.link(l).to_dict() for l in lines]
    return JSONResponse({"links": links, "summary": summarise(links, default_catalog(), adults=adults)})


app.mount("/", StaticFiles(directory=os.environ.get("BONAPPETIT_SITE", ROOT / "site"), html=True), name="site")
