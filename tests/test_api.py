import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Each test gets its own empty database file.
    monkeypatch.setenv("BOND_API_DB", str(tmp_path / "test.db"))
    from app.main import app
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_bonds(client):
    bonds = client.get("/bonds").json()
    codes = [b["code"] for b in bonds]
    assert "R2032" in codes and "R2040" in codes
    assert bonds == sorted(bonds, key=lambda b: b["maturity"])


def test_unknown_bond_is_404(client):
    assert client.get("/bonds/R999").status_code == 404


def test_schedule_ends_with_redemption(client):
    r = client.get("/bonds/R2032/schedule", params={"settle": "2031-12-01"}).json()
    last = r["cash_flows"][-1]
    assert last["date"] == "2032-03-31"
    assert last["amount"] == pytest.approx(104.125)


def test_price_and_yield_round_trip(client):
    p = client.get("/bonds/R2035/price", params={"settle": "2026-11-09", "ytm": 9.75}).json()
    y = client.get("/bonds/R2035/yield", params={"settle": "2026-11-09", "price": p["clean_price"]}).json()
    assert y["ytm_percent"] == pytest.approx(9.75, abs=1e-4)
    assert p["all_in_price"] == pytest.approx(p["clean_price"] + p["accrued_interest"], abs=1e-5)


def test_bad_input_is_rejected(client):
    assert client.get("/bonds/R2032/price", params={"settle": "not-a-date", "ytm": 9}).status_code == 422
    assert client.get("/bonds/R2032/price", params={"settle": "2026-11-09", "ytm": 500}).status_code == 422


def test_quote_crud(client):
    created = client.post("/quotes", json={"code": "r2032", "settle": "2026-11-09", "ytm_percent": 8.9})
    assert created.status_code == 201
    q = created.json()
    assert q["code"] == "R2032" and q["clean_price"] > 0

    assert client.get(f"/quotes/{q['id']}").json()["id"] == q["id"]
    assert len(client.get("/quotes", params={"code": "R2032"}).json()) == 1

    assert client.delete(f"/quotes/{q['id']}").status_code == 204
    assert client.get(f"/quotes/{q['id']}").status_code == 404


def test_quote_for_unknown_bond_is_404(client):
    r = client.post("/quotes", json={"code": "R999", "settle": "2026-11-09", "ytm_percent": 9})
    assert r.status_code == 404
