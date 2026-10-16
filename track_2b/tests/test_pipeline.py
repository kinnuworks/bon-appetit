"""Linker, ledger and server with a stub model, so the tests need no network and no GPU."""
from fastapi.testclient import TestClient

from bonappetit.catalog import Catalog
from bonappetit.ledger import summarise
from bonappetit.linker import Linker
from bonappetit.receipt import make_line


class StubModel:
    """Answers like Apertus would: read first, then pick the first candidate."""

    def __init__(self, choice=1, food=True):
        self.choice, self.food = choice, food

    def json(self, messages, schema, max_tokens=300):
        keys = schema["properties"]
        if "german_food_name" in keys:
            return {"english": "whole milk", "german_food_name": "Vollmilch, UHT", "language": "de", "is_food": self.food}
        if "choice" in keys:
            return {"choice": self.choice, "sure": True}
        if "energy_kcal" in keys:
            return {}
        return {"text": "Zu wenig {LOW_PCT} Gemüse."}


CAT = Catalog(use_embeddings=False)


def test_links_milk_and_counts_grams():
    link = Linker(CAT, StubModel()).link(make_line("M-BUDG VOLLMILCH UHT 1L", qty=2))
    assert link.status == "linked" and "milch" in link.choice["name"].lower()
    s = summarise([link.to_dict()], CAT, adults=1, days=1)
    assert s["grams_per_adult_day"]["dairy"] > 1900


def test_answer_zero_goes_to_review():
    link = Linker(CAT, StubModel(choice=0)).link(make_line("XYZ 123"))
    assert link.status == "review" and link.question


def test_nonfood_is_set_aside():
    link = Linker(CAT, StubModel(food=False)).link(make_line("TRAGTASCHE 35L"))
    assert link.status == "nonfood" and link.choice is None


def test_server_health_and_analyze(monkeypatch):
    from bonappetit import server
    monkeypatch.setattr(server, "_llm", StubModel())
    monkeypatch.setattr(server, "default_catalog", lambda: CAT)
    client = TestClient(server.app)
    assert client.get("/api/health").status_code == 200
    r = client.post("/api/analyze", data={"text": "M-BUDG VOLLMILCH UHT 1L 1.35\nTRAGTASCHE 0.30", "adults": "1"})
    body = r.json()
    assert r.status_code == 200 and len(body["links"]) == 2
    assert body["summary"]["lines_nonfood"] == 1


def test_cross_check_keeps_pick_unless_clearly_worse():
    from bonappetit.linker import cross_check
    recs = {1: {"energy_kcal": 400, "fat": 30}, 2: {"energy_kcal": 60, "fat": 3}}
    nut = recs.__getitem__
    # the estimate looks like milk: the cross-check moves from the 400 kcal pick to the 60 kcal candidate
    assert cross_check(1, [1, 2], {"energy_kcal": 65, "fat": 3.5}, nut) == 2
    # the estimate is close to the pick: it stays
    assert cross_check(1, [1, 2], {"energy_kcal": 380, "fat": 28}, nut) == 1
    # no estimate: the pick stays
    assert cross_check(1, [1, 2], {}, nut) == 1


def test_upload_csv_route(monkeypatch):
    from bonappetit import server
    monkeypatch.setattr(server, "_llm", StubModel())
    monkeypatch.setattr(server, "default_catalog", lambda: CAT)
    client = TestClient(server.app)
    csv = "Artikel;Menge;Umsatz\nM-BUDG VOLLMILCH UHT 1L;2;2.70\n"
    r = client.post("/api/analyze", files={"file": ("bons.csv", csv, "text/csv")}, data={"adults": "2"})
    assert r.status_code == 200 and r.json()["links"][0]["line"]["qty"] == 2
