import os

import pytest
from fastapi.testclient import TestClient

# Set TEST_DATABASE_URL (as CI does) to run every test against PostgreSQL instead of SQLite.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    if TEST_DATABASE_URL:
        monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
        from app import db
        with db.connect() as conn:                      # start each test with an empty table
            conn.execute("TRUNCATE quotes RESTART IDENTITY")
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("BOND_API_DB", str(tmp_path / "test.db"))   # a fresh SQLite file per test
    from app.main import app
    return TestClient(app)


def test_health(client):
    expected = "postgresql" if TEST_DATABASE_URL else "sqlite"
    assert client.get("/health").json() == {"status": "ok", "database": expected}


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


def test_quotes_are_listed_newest_first_and_filtered(client):
    for code, ytm in [("R2032", 8.9), ("R2040", 10.1), ("R2032", 9.0)]:
        client.post("/quotes", json={"code": code, "settle": "2026-11-09", "ytm_percent": ytm})
    r2032 = client.get("/quotes", params={"code": "r2032"}).json()
    assert [q["ytm_percent"] for q in r2032] == [9.0, 8.9]
    assert len(client.get("/quotes", params={"limit": 2}).json()) == 2


def test_deleting_a_missing_quote_is_404(client):
    assert client.delete("/quotes/999999").status_code == 404


# --- repo rate ---------------------------------------------------------------------------------

def test_latest_repo_rate(client):
    r = client.get("/rates/repo").json()
    assert r["on"] is None
    assert r["repo_rate_percent"] == 7.25
    assert r["prime_rate_percent"] == 10.75
    assert r["decision"]["announced"] == "2026-09-23"
    assert r["decision"]["change_bp"] == 25
    assert r["decision"]["source"].startswith("https://")


@pytest.mark.parametrize("day, expected", [
    ("2024-09-18", 8.25),   # the day before the first cut of the cycle
    ("2024-09-19", 8.00),   # a decision applies from its announcement date
    ("2026-01-01", 6.75),
    ("2026-07-23", 7.00),   # July 2026 held the rate, so May's 7.00 still applies
])
def test_repo_rate_on_a_date(client, day, expected):
    assert client.get("/rates/repo", params={"on": day}).json()["repo_rate_percent"] == expected


def test_repo_rate_outside_the_table_is_422(client):
    assert client.get("/rates/repo", params={"on": "2020-01-01"}).status_code == 422
    assert client.get("/rates/repo", params={"on": "2099-01-01"}).status_code == 422


def test_repo_history_is_ordered_with_moves_in_basis_points(client):
    h = client.get("/rates/repo/history").json()
    days = [c["announced"] for c in h["changes"]]
    assert days == sorted(days)
    assert h["changes"][0]["change_bp"] is None
    assert all(abs(c["change_bp"]) in (25, 50) for c in h["changes"][1:])
    assert all(c["source"].startswith("https://") for c in h["changes"])
