# Walkthrough

Read this before any interview where this project might come up.

## The big picture

A **REST API** lets other programs (a website, a spreadsheet, another service) ask questions over HTTP and get JSON back. This one wraps the bond calculator library: a request like `GET /bonds/R2032/price?settle=2026-11-09&ytm=8.9` runs the calculation and returns the answer as JSON.

## `app/main.py`: the routes

- `app = FastAPI(...)` creates the application. Its title and description appear in the auto-generated docs at `/docs`.
- Each `@app.get(...)`, `@app.post(...)` or `@app.delete(...)` **decorator** connects a URL and HTTP method to a Python function.
- `{code}` in a path is a **path parameter**; `settle`, `ytm` and `price` are **query parameters** (after the `?`).
- `Query(..., gt=-50, lt=100)`: `...` means required; `gt`/`lt` set limits. FastAPI rejects out-of-range values with a 422 before your code runs.
- `settle: date`: FastAPI converts the text `2026-11-09` into a Python `date`, and rejects anything that isn't a valid date.
- `response_model=...` tells FastAPI the shape of the response, so it validates the output and documents it.
- `_bond_or_404()` turns the library's `KeyError` into an **HTTP 404** ("not found"), which is the correct status for an unknown resource.
- `status_code=201` on `POST /quotes` means "created"; `204` on `DELETE` means "done, nothing to return".
- **CORS middleware**: browsers block a web page from calling an API on a different domain unless the API allows it. This lets Project 3's website call the API.

*Likely questions:* "What's the difference between 404 and 422?" (404: the thing doesn't exist; 422: the request is malformed or invalid). "Why GET for price but POST for quotes?" (GET reads without changing anything; POST creates a new record).

## `app/schemas.py`: data shapes

**Pydantic models** describe the JSON going in and out. `Field(gt=..., lt=..., max_length=...)` adds validation rules. `QuoteOut(QuoteIn)` **inherits** all the input fields and adds `id`, `clean_price` and `created_at`.

## `app/db.py`: the database

- Uses SQLite, a database stored in a single file, through Python's built-in `sqlite3`.
- `connect()` is a **context manager** (`with connect() as conn:`): it opens the connection, creates the table if it doesn't exist, commits on success and always closes the connection, even after an error.
- `row_factory = sqlite3.Row` lets rows be converted to dictionaries.
- Every query uses `?` **placeholders** with values passed separately. This prevents **SQL injection**, where a malicious input like `'; DROP TABLE quotes; --` would otherwise be run as SQL.
- The database path comes from the `BOND_API_DB` environment variable, so tests and production use different files.

## `tests/test_api.py`: the tests

- A **pytest fixture** (`client`) gives every test a fresh `TestClient` and its own empty database in a temporary folder (`tmp_path`, `monkeypatch.setenv`).
- `TestClient` sends requests to the app in memory, without starting a server.
- The tests cover: the health check, listing and sorting bonds, 404s, the final cash flow, a price-to-yield round trip, 422s for bad input, and the full create-read-list-delete cycle for quotes.

## `Dockerfile`: packaging

Starts from a slim Python image, installs `git` (needed to install the calculator from GitHub), installs the requirements, copies the app and starts `uvicorn` on the port the host provides (`$PORT`, default 8000). Copying `requirements.txt` before the code means Docker can reuse the cached install step when only the code changes.

## `.github/workflows/tests.yml`: CI

Two jobs on every push: lint and test on Python 3.10 and 3.12, and build the Docker image.

## Ideas to extend it yourself

1. Add a `/bonds/{code}/duration` endpoint.
2. Add an API key check for `POST` and `DELETE`.
3. Swap SQLite for Postgres using an environment variable for the connection string.
4. Deploy it on Render and add the live link to the README.
