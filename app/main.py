"""RSA Bond API: a REST API over the rsabond library, with SQLite or PostgreSQL storage for yield quotes
and a sourced table of SARB repo rate decisions.

Run locally:  uvicorn app.main:app --reload     then open http://127.0.0.1:8000/docs
"""

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rsabond import (
    BONDS,
    accrued_interest,
    all_in_price,
    clean_price,
    get_bond,
    is_ex_coupon,
    schedule,
    yield_from_price,
)

from . import db, rates
from .schemas import (
    BondOut,
    CashFlow,
    PriceOut,
    QuoteIn,
    QuoteOut,
    RepoChangeOut,
    RepoHistoryOut,
    RepoRateOut,
    ScheduleOut,
    YieldOut,
)

app = FastAPI(
    title="RSA Bond API",
    version="0.2.0",
    description="Coupon schedules, accrued interest, prices and yields for South African government bonds, "
                "plus storage for yield quotes and the SARB repo rate history. "
                "Prices approximate, but are not identical to, JSE formulas.",
)

# Allow a browser front end (Project 3) hosted on another domain to call this API.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


def _bond_or_404(code: str):
    try:
        return get_bond(code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown bond {code!r}") from None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": db.backend()}


@app.get("/bonds", response_model=list[BondOut])
def list_bonds():
    return [_bond_out(b) for b in sorted(BONDS.values(), key=lambda b: b.maturity)]


@app.get("/bonds/{code}", response_model=BondOut)
def read_bond(code: str):
    return _bond_out(_bond_or_404(code))


@app.get("/bonds/{code}/schedule", response_model=ScheduleOut)
def read_schedule(code: str, settle: date = Query(..., description="Settlement date, YYYY-MM-DD")):
    bond = _bond_or_404(code)
    flows = [CashFlow(date=d, amount=round(a, 6)) for d, a in schedule(bond, settle)]
    return ScheduleOut(code=bond.code, settle=settle, cash_flows=flows)


@app.get("/bonds/{code}/price", response_model=PriceOut)
def read_price(code: str, settle: date, ytm: float = Query(..., gt=-50, lt=100, description="Yield in percent")):
    bond = _bond_or_404(code)
    y = ytm / 100
    return PriceOut(
        code=bond.code, settle=settle, ytm_percent=ytm,
        ex_coupon=is_ex_coupon(bond, settle),
        accrued_interest=round(accrued_interest(bond, settle), 6),
        clean_price=round(clean_price(bond, settle, y), 6),
        all_in_price=round(all_in_price(bond, settle, y), 6),
    )


@app.get("/bonds/{code}/yield", response_model=YieldOut)
def read_yield(code: str, settle: date, price: float = Query(..., gt=0, description="Clean price per R100")):
    bond = _bond_or_404(code)
    try:
        y = yield_from_price(bond, settle, price)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return YieldOut(code=bond.code, settle=settle, clean_price=price, ytm_percent=round(y * 100, 6))


@app.post("/quotes", response_model=QuoteOut, status_code=201)
def create_quote(quote: QuoteIn):
    bond = _bond_or_404(quote.code)
    price = clean_price(bond, quote.settle, quote.ytm_percent / 100)
    return db.insert_quote(bond.code, quote.settle.isoformat(), quote.ytm_percent, round(price, 6), quote.source)


@app.get("/quotes", response_model=list[QuoteOut])
def read_quotes(code: str | None = None, limit: int = Query(100, ge=1, le=1000)):
    return db.list_quotes(code.upper() if code else None, limit)


@app.get("/quotes/{quote_id}", response_model=QuoteOut)
def read_quote(quote_id: int):
    q = db.get_quote(quote_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q


@app.delete("/quotes/{quote_id}", status_code=204)
def remove_quote(quote_id: int):
    if not db.delete_quote(quote_id):
        raise HTTPException(status_code=404, detail="Quote not found")


@app.get("/rates/repo", response_model=RepoRateOut)
def read_repo_rate(on: date | None = Query(None, description="Date, YYYY-MM-DD; omit for the latest decision")):
    """The SARB repo rate (and prime) in force on a date, with the decision that set it and its source."""
    if on is not None and on > rates.DATA_AS_OF:
        raise HTTPException(status_code=422,
                            detail=f"Repo rate data is only checked up to {rates.DATA_AS_OF.isoformat()}")
    try:
        change = rates.rate_on(on or rates.DATA_AS_OF)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return RepoRateOut(on=on, repo_rate_percent=change.rate_percent,
                       prime_rate_percent=change.rate_percent + rates.PRIME_SPREAD,
                       decision=_change_out(change), data_as_of=rates.DATA_AS_OF)


@app.get("/rates/repo/history", response_model=RepoHistoryOut)
def read_repo_history():
    """Every repo rate change in the table, oldest first. Meetings that left the rate unchanged are omitted."""
    return RepoHistoryOut(
        data_as_of=rates.DATA_AS_OF,
        note="Changes only; decisions that held the rate are omitted. Official figures: https://www.resbank.co.za",
        changes=[_change_out(c) for c in rates.REPO_CHANGES],
    )


def _change_out(c: rates.RepoChange) -> RepoChangeOut:
    return RepoChangeOut(announced=c.announced, repo_rate_percent=c.rate_percent,
                         change_bp=rates.change_bp(c), source=c.source)


def _bond_out(b) -> BondOut:
    return BondOut(code=b.code, coupon_percent=round(b.coupon * 100, 4), maturity=b.maturity,
                   coupon_dates=[f"{d:02d}/{m:02d}" for m, d in b.coupon_days])
