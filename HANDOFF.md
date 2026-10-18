# imagetool — handoff

Last updated 2026-10-18. Read this first, then `README.md` (setup + architecture) and `TODO.md`.
The design decisions (D1–D17) and the vocabulary (Listing, Run, Run Spec, Signal, …) are in
`docs/grilling-output.md`.

## Start here

Open Claude Code **on the Windows laptop**, in this repo, and say:

> Read HANDOFF.md. Then look at `C:\Users\User\Documents\Work\Vinted-New-Notif` and build
> task 1 (Vinted adapter), then task 2 (UI).

This has to run locally because the Vinted project only exists on that machine.

## State

| Area | Status |
|------|--------|
| Pipeline: Run Spec → Source Adapter → dedupe → engines → signals → category → identity → SQLite | Done, tested |
| Run modes `new_only` / `backfill` | Done, tested |
| Keyword dictionaries (el, bg, hr, ro, et, en) × 4 categories | Done (`imagetool/classify/keywords/*.json`) |
| Identifiers: Yu-Gi-Oh (name + set), vinyl, board game, electronics | Done, tested |
| API: `/runs`, `/runs/{id}`, `/runs/{id}/classifications`, `/listings/{id}`, `/listings/{id}/images/{n}`, `/options`, `/health` | Done, tested |
| CLI: `run <spec.yaml>`, `benchmark`, `catalog refresh / load-sample` | Done |
| Mock marketplace (28 listings, 6 languages) + benchmark | Done: 100 % on fixtures (a regression check, not real accuracy) |
| **Vinted adapter** | **Not started**: task 1 |
| **Web UI** (`imagetool/web/index.html`) | **Not started**: task 2. `GET /` fails until it exists |
| Tesseract OCR / CLIP engines | Written, **never run** (no Tesseract or GPU in the cloud session): task 3 |
| `catalog refresh` (YGOPRODeck download) | Written, **never run** (network blocked): task 3 |

Tests: `python -m pytest` (50 pass). Benchmark: `python -m imagetool.cli benchmark`.

## Tasks, in order

### 1. Vinted Source Adapter: `imagetool/sources/vinted.py`

First read how `Vinted-New-Notif` fetches listings: endpoints, session cookie / token,
headers, rate limiting, paging, and the item JSON fields. Mirror its approach rather than
inventing one.

- Implement the `SourceAdapter` port (`imagetool/domain/ports.py`):
  - `name = "vinted"`.
  - `fetch(spec)` yields `Listing`s **newest first**, paging lazily. It **must not cap the
    count**: `RunService` stops on `max_listings` / `max_scanned` / the first seen listing
    (`new_only`).
  - `fetch_image(url)` returns the photo bytes using the same session.
- Map the RunSpec to Vinted parameters: `query` → search text, `price` → price range,
  `countries` → which Vinted domain(s) (vinted.gr, .hr, .ro, .ee, …; check which exist).
- Map each item to a `Listing`: `source_listing_id`, title, description, price, currency,
  country, posted_at, url, photo URLs. Put brand, Vinted category, size and condition into
  `raw_attributes`. `raw_attributes["category"]` already becomes a classification signal.
- Descriptions may only be on the item page, not in search results. If Vinted-New-Notif
  fetches them separately, do the same (one request per *new* listing is fine; dedupe
  already skips seen ones).
- Register it in `imagetool/sources/__init__.py`.
- Tests: save 1–2 real responses into `fixtures/vinted/` and test the mapping and paging
  offline with a fake HTTP layer. Tests must never call Vinted.

### 2. Web UI: `imagetool/web/index.html`

One static page served by `GET /` (route already in `imagetool/routes/ui.py`), vanilla JS,
no build step.

- **Form:** source (from `GET /options`), mode (*New listings only* / *Scan older unseen*),
  search, category checkboxes, countries, price min/max, "classify up to"
  (`max_listings`), min confidence.
- **Run once:** `POST /runs` → poll `GET /runs/{id}` until `done`/`failed` → show
  `GET /runs/{id}/classifications` as cards. Each card has: image
  (`/listings/{id}/images/0`), category badge, confidence %, bundle ×N, title linking to
  `source_url`, price/country/language, identity fields, and a "Why?" toggle that loads
  signals + OCR text from `GET /listings/{id}`.
- **Watch:** repeat a `new_only` Run every N seconds and add new cards to the top,
  highlighted.
- **Recent runs list** (`GET /runs`); clicking one loads its classifications. Add category
  filter chips with counts.
- Listing titles come from external sites: build DOM with `textContent`, **never `innerHTML`**.
- Light and dark theme through CSS variables. It must work at phone width.
- Add a test that `GET /` returns 200 with HTML.

### 3. Real engines and real card data (on the laptop)

- `python -m imagetool.cli catalog refresh` loads the full YGOPRODeck snapshot (en + de, fr,
  it, pt names). Then check that name matching speed is acceptable with ~13k cards × 5 languages
  (`SqliteCardCatalog.match_name`).
- Install Tesseract and the CUDA build of PyTorch + open_clip (README "Setup on Windows"), set
  `IMAGETOOL_OCR=tesseract` and `IMAGETOOL_IMAGE_CLASSIFIER=clip`, and run real Vinted listings.
- Label ~50 real listings as a second benchmark. The fixture benchmark is not real
  accuracy. Pass bar: 80 % category, 80 % card name + set (D12).

## Things to know

- **Engines default to `fixture`.** They only know the mock listings' image URLs. On real
  listings they return nothing, so only text signals count. Switch to real engines (task 3)
  for photo evidence.
- **Layering:** `classify/` and `identify/` are pure, with no I/O. Engines, adapters and the
  catalog come in through ports. Routes are thin and SQL lives in `services/repository.py`.
  Adding a site means adding an adapter. Adding a category means a keyword JSON, an
  Identifier, and CLIP prompts.
- **Dedupe (D8):** same `(source, source_listing_id)` + same content hash + same price →
  skipped. A price or content change → re-classified, and the price is kept in
  `listing_prices`.
- **Images (D14/D16):** only a 512 px JPEG copy is stored (`data/images/<listing_id>/`), plus
  the raw OCR text. To tune rules, re-score from the stored OCR text; re-running OCR needs a
  re-download.
- **Card sample data** (`fixtures/ygoprodeck_sample/`) was written from memory and may have
  wrong codes. Tests depend on it; real runs should use `catalog refresh`.
- **Tests** follow Arrange / Act / Assert. Each test gets its own temp DB and a copy of the
  fixtures (`tests/conftest.py`).

## Run it

```powershell
git clone https://github.com/kintokann-oss/imagetool
cd imagetool
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
python -m imagetool.cli run specs/example.yaml
uvicorn imagetool.main:create_app --factory --reload   # http://127.0.0.1:8000/docs
```

## History

The design was worked out in a grilling session (`docs/grilling-output.md`), and the app was
first built in `kintokann-oss/grill-with-docs-flow` on branch
`claude/image-classification-listings-4250nz` (`apps/imagetool/`). It moved here on 2026-10-18.
