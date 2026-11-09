# rsa-bond-api

![tests](https://github.com/sihlangu-mthembu/rsa-bond-api/actions/workflows/tests.yml/badge.svg)

A REST API for South African government bond analytics, built with **FastAPI**, stored in **PostgreSQL** (or SQLite with no setup) and packaged with **Docker**. It serves coupon schedules, accrued interest, prices and yields from the [rsa-bond-calculator](https://github.com/sihlangu-mthembu/rsa-bond-calculator) library, stores yield quotes in a database, and returns the South African Reserve Bank repo rate on any date since March 2023, with a source for every figure.

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Health check, and which database is in use |
| GET | `/bonds` | All bonds, sorted by maturity |
| GET | `/bonds/{code}` | One bond's coupon, maturity and coupon dates |
| GET | `/bonds/{code}/schedule?settle=YYYY-MM-DD` | Remaining cash flows per R100 |
| GET | `/bonds/{code}/price?settle=…&ytm=8.9` | Accrued interest, clean and all-in price |
| GET | `/bonds/{code}/yield?settle=…&price=97.5` | Yield from a clean price |
| POST | `/quotes` | Save a yield quote (the clean price is calculated and stored) |
| GET | `/quotes?code=R2032` | List saved quotes |
| GET | `/quotes/{id}` | One quote |
| DELETE | `/quotes/{id}` | Delete a quote |
| GET | `/rates/repo` | Latest SARB repo rate and prime, with the decision that set it |
| GET | `/rates/repo?on=2025-06-01` | The repo rate in force on a date |
| GET | `/rates/repo/history` | Every repo rate change since March 2023, each with a source link |

Interactive documentation is generated automatically at `/docs`.

**Live API:** https://rsa-bond-api.onrender.com/docs (free host: the first request after a quiet spell takes about a minute while it wakes up).

Example:

```bash
$ curl "http://127.0.0.1:8000/bonds/R2032/price?settle=2026-11-09&ytm=8.9"
{"code":"R2032","settle":"2026-11-09","ytm_percent":8.9,"ex_coupon":false,
 "accrued_interest":0.90411,"clean_price":97.221481,"all_in_price":98.12559}
```

## Run it

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
pytest -q                            # 17 tests, on SQLite
```

With Docker:

```bash
docker build -t rsa-bond-api .
docker run -p 8000:8000 rsa-bond-api
```

With PostgreSQL (Docker Compose starts the database and the API together, and quotes survive restarts):

```bash
docker compose up --build             # http://localhost:8000/docs
```

To run the tests against PostgreSQL, point `TEST_DATABASE_URL` at an empty database:

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bonds pytest -q
```

## Design notes

- **Validation:** Pydantic models reject bad input with a 422 (a malformed date, a yield of 500%). Unknown bond codes return 404.
- **Database:** if `DATABASE_URL` is set, quotes go to PostgreSQL through `psycopg` 3; otherwise to SQLite through Python's built-in `sqlite3` (file path from `BOND_API_DB`). Both run the same parameterised SQL (no string-built queries), so the switch lives in one small wrapper in `app/db.py`. CI runs the full test suite against both.
- **Repo rate data:** `app/rates.py` holds every Monetary Policy Committee decision that changed the rate since March 2023, each with the news report it was checked against and a `DATA_AS_OF` date. It is reference data, not a live feed: after each MPC meeting, add a row and bump the date. Dates after `DATA_AS_OF` return 422 rather than a possibly stale answer. Prime is shown as repo + 3.5 points, the South African convention.
- **CORS** is open so a browser front end on another domain can call the API.
- **CI** runs the linter, mypy and the tests on Python 3.10 and 3.12, runs the tests again against a PostgreSQL 16 service container, and builds the Docker image on every push.
- Prices approximate, but are not identical to, the JSE's official bond pricing formula. See the calculator's README for the conventions.

## Deploying (free)

On [Render](https://render.com): New → Web Service → connect this repo → it detects the Dockerfile → deploy. The free tier sleeps when idle and does not keep the SQLite file between restarts. For persistent quotes, create a Render PostgreSQL database and set the web service's `DATABASE_URL` to its connection string; no code change is needed. (Check Render's current terms for free databases before relying on one.)

## About

Built with AI assistance (Claude) by Sihlangu Mthembu. See `WALKTHROUGH.md` for a file-by-file explanation.
