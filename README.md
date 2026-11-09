# rsa-bond-api

![tests](https://github.com/sihlangu-mthembu/rsa-bond-api/actions/workflows/tests.yml/badge.svg)

A REST API for South African government bond analytics, built with **FastAPI** and **SQLite** and packaged with **Docker**. It serves coupon schedules, accrued interest, prices and yields from the [rsa-bond-calculator](https://github.com/sihlangu-mthembu/rsa-bond-calculator) library, and stores yield quotes in a database.

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Health check |
| GET | `/bonds` | All bonds, sorted by maturity |
| GET | `/bonds/{code}` | One bond's coupon, maturity and coupon dates |
| GET | `/bonds/{code}/schedule?settle=YYYY-MM-DD` | Remaining cash flows per R100 |
| GET | `/bonds/{code}/price?settle=…&ytm=8.9` | Accrued interest, clean and all-in price |
| GET | `/bonds/{code}/yield?settle=…&price=97.5` | Yield from a clean price |
| POST | `/quotes` | Save a yield quote (the clean price is calculated and stored) |
| GET | `/quotes?code=R2032` | List saved quotes |
| GET | `/quotes/{id}` | One quote |
| DELETE | `/quotes/{id}` | Delete a quote |

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
pytest -q                            # 8 tests
```

With Docker:

```bash
docker build -t rsa-bond-api .
docker run -p 8000:8000 rsa-bond-api
```

## Design notes

- **Validation:** Pydantic models reject bad input with a 422 (a malformed date, a yield of 500%). Unknown bond codes return 404.
- **Database:** SQLite through Python's built-in `sqlite3`, with parameterised queries (no string-built SQL). The file location comes from the `BOND_API_DB` environment variable, so each test uses its own temporary database.
- **CORS** is open so a browser front end on another domain can call the API.
- **CI** runs the linter and tests on Python 3.10 and 3.12 and builds the Docker image on every push.
- Prices approximate, but are not identical to, the JSE's official bond pricing formula. See the calculator's README for the conventions.

## Deploying (free)

On [Render](https://render.com): New → Web Service → connect this repo → it detects the Dockerfile → deploy. The free tier sleeps when idle and does not keep the SQLite file between restarts; for persistent quotes, attach a disk mounted at `/data` or move to Postgres.

## About

Built with AI assistance (Claude) by Sihlangu Mthembu. See `WALKTHROUGH.md` for a file-by-file explanation.
