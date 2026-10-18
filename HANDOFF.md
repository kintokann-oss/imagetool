# imagetool — handoff

Read this first, then `README.md` (setup and architecture) and `TODO.md` (progress).
Design decisions D1–D17 are in `docs/grilling-output.md`.

## Where things stand

- **Works and tested (50 tests, `python -m pytest`):** the full pipeline against the mock
  marketplace. Run Spec → Source Adapter → dedupe → OCR / image engines → keyword signals in
  6 languages → category vote → per-category Identifier (+ Yu-Gi-Oh catalog) → SQLite.
  There is a FastAPI API (`uvicorn imagetool.main:create_app --factory`) and a CLI
  (`python -m imagetool.cli run|benchmark|catalog`).
- **Written but never run:** `engines/tesseract.py` and `engines/clip.py` (the cloud container
  had no Tesseract, torch or GPU), and `catalog refresh` (ygoprodeck.com was blocked). Run these
  on the laptop first; see README "Setup on Windows".
- **Card data:** `fixtures/ygoprodeck_sample/` is a 9-card sample written from memory and may
  have wrong set codes. Use `python -m imagetool.cli catalog refresh` for real data.

## Last session's unfinished work (in this commit, tests still pass)

1. **Run modes (done):** `RunSpec.mode`:
   - `new_only`: the adapter yields newest first, and the Run **stops at the first listing
     already in the DB**. This is the notifier behaviour.
   - `backfill`: keeps scanning past already-seen listings and classifies older unseen ones.
     Unchanged listings are skipped; changed content or price is re-classified (D8).
   - Limits: `max_listings` caps how many get classified per Run, and `max_scanned` caps how
     many get looked at. **Adapters must not cap results and must yield newest first**
     (contract in `domain/ports.py: SourceAdapter`).
2. **API for the UI (done):** `GET /runs?limit=` (recent runs), `GET /options` (sources,
   categories, modes), `GET /listings/{id}/images/{position}` (stored 512 px JPEG),
   `GET /` (serves `imagetool/web/index.html`).
3. **Not done: `imagetool/web/index.html` does not exist yet**, so `GET /` fails until it is
   written. The plan for it was one static page, vanilla JS, no build step:
   - A form with: source, mode (New listings only / Scan older unseen), search text, category
     checkboxes, countries, price min/max, "classify up to", min confidence.
   - "Run once" does `POST /runs`, polls `GET /runs/{id}` until `done`, then shows
     `GET /runs/{id}/classifications` as cards: image, category badge, confidence, bundle,
     identity fields, and a "Why?" toggle that loads signals + OCR text from `GET /listings/{id}`.
   - "Watch" repeats a `new_only` Run every N seconds and adds new results to the top.
   - A recent-runs list; clicking one loads its classifications.
   - Build all DOM with `textContent`, never `innerHTML`, because titles come from external sites.
4. **Not done: Vinted Source Adapter.** The user's project
   `C:\Users\User\Documents\Work\Vinted-New-Notif` already fetches Vinted listings. Read how it
   does that (endpoints, cookies/session token, headers, rate limiting, paging, item JSON
   fields), then write `imagetool/sources/vinted.py`:
   - `name = "vinted"`. `fetch(spec)` pages through the catalog search **newest first**,
     maps the RunSpec (query, price, countries → Vinted domain/locale) to Vinted parameters,
     and maps each item to `Listing`: id, title, description, price, currency, country,
     posted_at, url, photo URLs, and brand/category/size into `raw_attributes`.
   - `fetch_image(url)` downloads the photo with the same session.
   - Register it in `sources/__init__.py`. Respect whatever throttling the Vinted project
     uses; backfill can scan many pages.
   - Vinted item descriptions are often only on the item page, not in search results. If the
     Vinted project fetches them separately, decide whether to do that too (cost: one request
     per listing).
   - Tests: record a couple of real JSON responses into `fixtures/vinted/` and test the
     mapping offline. Don't call Vinted from tests.

## Run it

```powershell
git clone https://github.com/kintokann-oss/imagetool
cd imagetool
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
python -m imagetool.cli benchmark
uvicorn imagetool.main:create_app --factory --reload   # http://127.0.0.1:8000/docs
```

The default engines are `fixture`: they only know the mock listings. For Vinted, set
`IMAGETOOL_OCR=tesseract` and `IMAGETOOL_IMAGE_CLASSIFIER=clip` (README has the install steps).
With the fixture engines, real listings get no OCR or image evidence, only text signals.

## Git

This repo is `kintokann-oss/imagetool`. It was first built on branch
`claude/image-classification-listings-4250nz` of `kintokann-oss/grill-with-docs-flow` (in
`apps/imagetool/`), then moved here as one commit.
