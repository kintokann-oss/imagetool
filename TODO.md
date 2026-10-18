# imagetool — TODO

Built from `docs/grilling-output.md` (decisions D1–D17). Checked = done and tested.

## Foundation
- [x] Project skeleton: FastAPI app, config from env, SQLite + migrations, `/health`
- [x] Domain models: `Listing`, `RunSpec`, `Category`, `Signal`, `Classification`, `ItemIdentity`
- [x] Ports: `SourceAdapter`, `OcrEngine`, `ImageClassifier`, `CardCatalog`

## Sources
- [x] Mock marketplace fixtures: ~30 listings across 6 languages + hard cases, generated images, expected results
- [x] `MockMarketplaceAdapter` applying Run Spec filters (query, countries, price, dates, limit)

## Classification core (pure, no I/O)
- [x] Text normalization + listing language detection (el, bg, hr, ro, et, en)
- [x] Keyword dictionaries per category × language (D6)
- [x] Signals from title, description, OCR text, image scores, source category
- [x] `CategoryClassifier`: weighted vote, category restriction, `min_confidence` → `unknown`
- [x] Bundle detection: `is_bundle` + `estimated_item_count` (D10)

## Identifiers (D3, D7)
- [x] Yu-Gi-Oh: set code, print language, edition, card name + set name via catalog, fuzzy OCR name correction
- [x] Vinyl: artist, title, format, year, label (incl. regional labels), catalog number
- [x] Board game: title, publisher, language edition
- [x] Electronics: product type, brand, model

## Card catalog (D11, D15)
- [x] SQLite tables for cards, translated names, prints/sets
- [x] Loader for YGOPRODeck `cardinfo.php` JSON (EN + `language=de|fr|it|pt`)
- [ ] `catalog refresh` command (network) — written, **not yet run** (YGOPRODeck blocked here); bundled sample snapshot done

## Engines (D5, D13)
- [x] Fixture engines (OCR text / image scores from the mock fixtures) for tests and dev without models
- [ ] `TesseractOcrEngine` (optional dep, langs picked from listing language) — written, **not yet run against Tesseract** (not installed here)
- [ ] `ClipImageClassifier` (optional dep, CUDA if available, CPU fallback) — written, **not yet run against a real model** (no torch/GPU here)

## Run pipeline
- [x] Dedupe: skip when content hash + price unchanged; re-classify and record price otherwise (D8)
- [x] Image store: 512 px JPEG copy + URL; raw OCR text stored per image (D14, D16)
- [x] `RunService`: fetch → dedupe → signals → classify → identify → persist, with counters

## API + CLI
- [x] `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/classifications`, `GET /listings/{id}`
- [x] CLI: `run <spec.yaml>`, `catalog refresh`, `benchmark`

## Quality
- [x] Benchmark over fixtures: category ≥ 80 %, Yu-Gi-Oh name + set ≥ 80 % (D12)
- [x] README with Windows setup (venv, Tesseract installer + language packs, PyTorch CUDA)

## Next
- [ ] Try real engines on the laptop: Tesseract + CLIP on actual listing photos; label ~50 real listings as a second benchmark
- [ ] OCR card prints with the print's language pack too (deu/fra/ita), not only the listing's language
- [ ] Faster fuzzy name matching once the full YGOPRODeck catalog (~13k cards × 5 languages) is loaded — measure first

## Later (not now)
- Scheduled runs · Discogs / BGG catalogs · LLM engine · per-image bundle classification · real site adapters · Docker
