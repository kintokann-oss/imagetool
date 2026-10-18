# Grilling Output — imagetool

> Phase 1 (UNDERSTAND) output for **imagetool**: a service that fetches used-item
> listings from marketplace websites and classifies each one (category + exact item)
> from its images (OCR + image classification) and its text (title, description, attributes).
>
> Status: **Phase 1 complete** — ready for Phase 2 (PRD).
> Target repo: `imagetool` (not created yet; this file lives here until it exists).

---

## 1. Decisions

| # | Decision | Source |
|---|----------|--------|
| D1 | Stack: Python, FastAPI, SQLite. No UI for now. | User |
| D2 | Listing languages: Greek, Croatian, Bulgarian, Romanian, Estonian, English (Latin + Greek + Cyrillic scripts). | User |
| D3 | Output = **category + identified item** (structured fields per category). Condition grading is out of scope. | User (Q1 = B) |
| D4 | The service **pulls** listings itself via **Source Adapters**, inside a **Run** driven by user-set conditions (**Run Spec**). The classification core only ever sees `Listing`, never site-specific data. | User (Q2 = A) |
| D5 | Engines are **local only** for now (OCR + CLIP-style image classifier + text rules). No LLM. Every engine sits behind an interface so an LLM can be added later. | User (Q3 = A) |
| D6 | Text understanding = hand-maintained **keyword dictionaries** per category × language. | User (Q4 = A) |
| D7 | Yu-Gi-Oh identification must return **both card name and set** (set code + set name). | User |
| D8 | Re-seen listing (same source + same source listing id): **skip if content and price are unchanged**; otherwise classify again and store the new price. | User (Q7) |
| D9 | First source is a **mock marketplace** (fixtures on disk). No real website yet. | User |
| D10 | **Bundles / lots:** one Classification per Listing, with `is_bundle` + `estimated_item_count`; Item Identity filled only for what the title/OCR names. Per-image classification possible later. | User (Q8 = A) |
| D11 | Yu-Gi-Oh reference data = **offline snapshot of YGOPRODeck** (free, no key) in SQLite, with a refresh command. Used for set code → set name and fuzzy-correcting OCR'd card names. | User (Q9 = A) |
| D13 | Runs on a **laptop with an RTX 3050** (laptop 3050 = 4–6 GB VRAM). Engines use CUDA when available and fall back to CPU (tests/CI run CPU-only with fake engines). | User (Q11 = B) |
| D14 | Images: keep a **downscaled copy + the source URL**; originals are discarded after classification. Re-classification after tuning runs on the stored copy. | User (Q12 = B) |
| D15 | Card Catalog includes **translated card names** (EN + the other languages the reference data offers), so a name printed in German/French/Italian matches directly; set code stays the primary key. | User (Q13 = B) |
| D16 | Kept image copy = **long edge 512 px** (~40 KB). Consequence: small text (set codes, catalog numbers) is not reliably readable from it, so **raw OCR output per image is stored** at first classification; re-tuning rules reuses stored OCR text instead of re-running OCR. Re-OCR needs a re-fetch from the URL. | User (Q14 = B) |
| D17 | Laptop runs **Windows**: run natively in a Python venv (Tesseract via Windows installer + language packs `ell hrv bul ron est eng deu fra ita spa por`; PyTorch CUDA wheels). Docker deferred. Paths and setup must work on Windows and Linux (CI). | User (Q15) |
| D12 | Pass bar for the fixture benchmark: **≥ 80%** for category accuracy and for Yu-Gi-Oh name + set both correct. To be tuned later. | User (Q10) |

### Assumed (recommended, not explicitly confirmed)

| # | Assumption | Why it's needed |
|---|------------|-----------------|
| A1 | Run Spec shape as in §4; Runs are started by hand (`POST /runs`); no scheduler yet. | Q5 unanswered |
| A2 | Identification for vinyl / board games / electronics = **structured field extraction only**, no catalog lookup yet. Catalogs come later behind a `Catalog` port. | Q6 unanswered (except cards, see D7 / Q9) |
| A3 | Below `min_confidence`, category = `unknown`; the listing is still stored with its signals. | Needed for D3 |

---

## 2. Ubiquitous Language (new terms)

| Term | Definition | Not |
|------|-----------|-----|
| **Listing** | One used-item post from a source, normalized: images, title, description, price, currency, country, posted_at, source_url, raw_attributes. | Not the identified item (that's an Item Identity). |
| **Source** | A website (or mock) that listings come from, e.g. `mock_marketplace`. | |
| **Source Adapter** | Turns one Source's search results into `Listing`s according to a Run Spec. Only place that knows site-specific formats. | Not a Catalog. |
| **Run** | One execution of fetch → dedupe → classify → store, with a status and counters. | |
| **Run Spec** | The user-set conditions of a Run (source, query, categories, countries, price, dates, limits, thresholds). | |
| **Category** | One of `vinyl`, `yugioh_card`, `board_game`, `electronics`, `unknown`. | Not a marketplace's own category field (that's a raw attribute / signal). |
| **Signal** | One piece of evidence for a Category or an identity field, with its origin (`title_keyword`, `ocr_keyword`, `image_label`, `source_category`, `pattern`) and weight. | |
| **Classification** | The result for one Listing in one Run: category, confidence, Item Identity, Signals. | |
| **Item Identity** | Category-specific structured fields naming the exact item (see §5). | |
| **Identifier** | Per-category component that builds an Item Identity from text + OCR. | |
| **Content Hash** | Hash of a Listing's title + description + image URLs; with price, decides skip vs re-classify (D8). | |
| **Engine** | A swappable model wrapper behind a port: `OcrEngine`, `ImageClassifier`. | |
| **Catalog** | A reference lookup behind a port. First one: `YgoCardCatalog` over a local YGOPRODeck snapshot (D11). Discogs/BGG later. | Not a Source. |
| **Bundle** | A Listing that sells several items at once (`is_bundle = true`). | Not a single-item Listing with many photos. |
| **OCR Result** | Raw text + boxes produced by the OcrEngine for one image, stored so Signals can be recomputed without the original image. | Not a Signal (Signals are derived from it). |
| **Benchmark** | The mock fixture set with expected Classifications, scored against the pass bar (D12). | |

---

## 3. Architecture sketch (ports & adapters)

```
            Run Spec
               │
               ▼
   ┌───────────────────────┐
   │ RunService            │  orchestrates one Run
   └─────────┬─────────────┘
             │ SourceAdapter.fetch(spec) ──► MockMarketplaceAdapter (fixtures)
             ▼                                (later: real site adapters)
        Listing[]
             │
             ▼
   Dedupe gate (source, source_listing_id, content_hash, price)  ── skip ──► counted
             │ new / changed
             ▼
   Signal extraction (all pure, engines injected)
     ├─ TextSignals:   lang detect → keyword dictionaries (cat × lang)
     ├─ OcrSignals:    OcrEngine (Tesseract, langs from listing lang + eng) → keywords + patterns
     ├─ ImageSignals:  ImageClassifier (CLIP zero-shot over category prompts)
     └─ SourceSignals: the site's own category/attributes, if any
             │
             ▼
   CategoryClassifier: weighted vote of Signals → category + confidence
             │ (restricted to spec.categories; < min_confidence → unknown)
             ▼
   Identifier registry: { vinyl, yugioh_card, board_game, electronics } → Item Identity
             │
             ▼
   Repository (SQLite): runs, listings, listing_images, classifications, signals
```

Rules:
- Core (signals, classifier, identifiers) has **no I/O and no site knowledge**; engines/adapters are injected.
- Adding a category = new keyword dictionary + new Identifier + new image prompts. No core changes.
- Adding a website = new Source Adapter. No core changes.
- Tests use `FakeOcrEngine` / `FakeImageClassifier` returning canned outputs, so the logic is testable without models.

---

## 4. Run Spec (assumed, A1)

```yaml
source: mock_marketplace
query: "yugioh"                    # optional free text
categories: [yugioh_card, vinyl]   # default: all four
countries: [GR, HR, BG, RO, EE]
price: {min: 0, max: 200, currency: EUR}
posted_after: 2026-10-01
max_listings: 100
min_confidence: 0.6
```

---

## 5. Item Identity per category

| Category | Fields | Main evidence |
|----------|--------|---------------|
| `yugioh_card` | `card_name`, `set_code` (e.g. `LOB-EN001`), `set_name`, `print_language` (from set code: EN/DE/FR/IT/SP/PT…), `edition` (1st / unlimited / limited), `rarity` (optional) | OCR: name bar at top, set code under the art (`^[A-Z0-9]{2,4}-[A-Z]{0,2}\d{3}$`); title text |
| `vinyl` | `artist`, `title`, `label`, `catalog_number`, `format` (LP / 12" / 7"), `year` | Title/description ("Artist – Title"), OCR of sleeve/label, catalog number patterns |
| `board_game` | `title`, `edition`, `publisher`, `language_edition` | Title, OCR of box front |
| `electronics` | `product_type`, `brand`, `model` | Brand dictionary + model patterns in title/OCR |

Each field carries its own confidence and the Signal it came from.

---

## 6. Mock marketplace

- `fixtures/mock_marketplace/listings.json` + `fixtures/mock_marketplace/images/…`
- ~5 listings per category per language, plus hard cases: bundles, wrong-category titles,
  text-free photos, Cyrillic/Greek titles, card printed in German sold from a Bulgarian listing.
- `MockMarketplaceAdapter` applies the Run Spec filters (query, countries, price, dates, limit).
- Each fixture also stores the **expected Classification**, so the fixture set doubles as an accuracy benchmark.

---

## 7. Scenarios

1. **Card identified**
   Given a Greek listing "Blue Eyes κάρτα 1η έκδοση" with a photo whose OCR reads "Blue-Eyes White Dragon" and "LOB-EN001",
   When a Run classifies it,
   Then category = `yugioh_card`, card_name = "Blue-Eyes White Dragon", set_code = "LOB-EN001", set_name = "Legend of Blue Eyes White Dragon", print_language = EN.

2. **Unchanged listing skipped (D8)**
   Given a listing already stored with content hash H and price 20 EUR,
   When a later Run fetches it with hash H and price 20 EUR,
   Then it is skipped and counted as `skipped_unchanged`.

3. **Price changed**
   Given the same listing now at 15 EUR,
   When a Run fetches it,
   Then it is classified again and the new price is stored.

4. **Low confidence**
   Given a listing with no matching keywords and an image classifier score of 0.4,
   When classified with `min_confidence: 0.6`,
   Then category = `unknown` and all Signals are stored.

5. **Category restriction**
   Given a Run Spec with `categories: [vinyl]`,
   When a listing looks like a board game,
   Then it is classified `unknown`, not `board_game`.

---

## 8. Proposed API (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/runs` | Start a Run from a Run Spec; returns run id |
| GET | `/runs/{id}` | Status + counters (fetched, skipped_unchanged, classified, unknown, failed) |
| GET | `/runs/{id}/classifications` | Classifications of the Run, filterable by category |
| GET | `/listings/{id}` | Listing + latest Classification + Signals |

---

## 9. ADR candidates

- ADR: Ports & adapters split (Source Adapter / Engine / Catalog ports; core has no I/O).
- ADR: Local-only engines first (Tesseract + CLIP), LLM deferred behind the same ports.
- ADR: Keyword dictionaries per category × language instead of multilingual embeddings (for now).
- ADR: Dedupe rule = (source, source_listing_id, content_hash, price).
- ADR: Store raw OCR text per image (because only a 512 px copy is kept).
- ADR: YGOPRODeck offline snapshot as the card Catalog (no runtime network dependency).

### Reference data notes (to verify at build time — network was blocked during grilling)

- YGOPRODeck API v7: `https://db.ygoprodeck.com/api/v7/cardinfo.php` (all cards, each with `card_sets[]`: `set_name`, `set_code`, `set_rarity`) and `.../cardsets.php` (all sets). No API key. They ask clients to download and cache data locally rather than call per request, rate-limit at ~20 req/s, and not hotlink card images.
- Translated names: the API accepts a `language` parameter (believed: `fr`, `de`, `it`, `pt`). The Yu-Gi-Oh TCG is not printed in Greek/Croatian/Bulgarian/Romanian/Estonian, so listings from those countries sell EN/DE/FR/IT/(ES/PT) prints.
- Set codes in the data are English (`LOB-EN001`); non-English prints (`LOB-DE001`) map by set prefix + card number.

---

## Open Questions

None blocking. Deferred to later issues: scheduled Runs, catalogs for vinyl (Discogs) / board games (BGG), LLM engine, per-image classification of bundles, real website adapters, Docker.
