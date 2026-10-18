# imagetool

Fetches used-item listings through **Source Adapters** and classifies each one as
`vinyl`, `yugioh_card`, `board_game`, `electronics` or `unknown`, then identifies the exact
item (for cards: name + set). It uses OCR text from the photos, an image classifier, and
the listing's title/description in Greek, Croatian, Bulgarian, Romanian, Estonian and English.

Design decisions: `docs/grilling-output.md` (D1–D17). Progress: [`TODO.md`](TODO.md).

## How it works

```
Run Spec ─► Source Adapter ─► Listing ─► dedupe (content hash + price)
                                           │ new / changed
                                           ▼
             images ─► OcrEngine + ImageClassifier ─► 512 px copy + OCR text stored
                                           ▼
             Signals (keywords per language, OCR keywords, set-code pattern, image scores)
                                           ▼
             CategoryClassifier ─► Identifier for that category (+ card Catalog) ─► SQLite
```

| Folder | What lives there |
|--------|------------------|
| `imagetool/domain/` | Models (`Listing`, `RunSpec`, `Signal`, `Classification`, …) and ports |
| `imagetool/sources/` | Source Adapters — only `mock_marketplace` for now |
| `imagetool/classify/` | Pure core: keyword dictionaries (`keywords/*.json`), signals, category vote, bundles |
| `imagetool/identify/` | One Identifier per category |
| `imagetool/catalog/` | Yu-Gi-Oh catalog over a local YGOPRODeck snapshot |
| `imagetool/engines/` | `fixture` / `tesseract` OCR, `fixture` / `clip` image classifier |
| `imagetool/services/` | `RunService` (pipeline) and SQL `repository` |
| `imagetool/routes/` | FastAPI routes |
| `fixtures/` | Mock marketplace (28 listings, 6 languages, expected results) + sample card data |

Adding a website = a new adapter in `sources/`. Adding a category = a keyword JSON, an
Identifier and CLIP prompts. The core does not change in either case.

## Setup on Windows (laptop with RTX 3050)

```powershell
git clone https://github.com/kintokann-oss/imagetool
cd imagetool
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
```

That runs everything with the **fixture engines**: no models are needed. To use real engines:

1. **Tesseract OCR.** Install the UB Mannheim Windows build. In the installer, tick the
   language packs Greek, Bulgarian, Croatian, Romanian, Estonian and English, plus German, French,
   Italian, Spanish and Portuguese for card prints. Then:
   ```powershell
   pip install -e ".[ocr]"
   $env:IMAGETOOL_OCR = "tesseract"
   $env:IMAGETOOL_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"   # if not on PATH
   ```
2. **CLIP on the GPU.** Install the CUDA build of PyTorch first, then open_clip:
   ```powershell
   pip install torch --index-url https://download.pytorch.org/whl/cu124
   pip install -e ".[vision]"
   $env:IMAGETOOL_IMAGE_CLASSIFIER = "clip"
   # optional, default ViT-B-32/laion2b_s34b_b79k; ViT-L-14 also fits a 4 GB 3050 in fp16
   $env:IMAGETOOL_CLIP_MODEL = "ViT-B-32/laion2b_s34b_b79k"
   ```
   It uses CUDA when `torch.cuda.is_available()`, otherwise the CPU.
3. **Real card data.** Download the YGOPRODeck snapshot (English plus de/fr/it/pt names):
   ```powershell
   python -m imagetool.cli catalog refresh
   ```
   Until you do this, a tiny hand-written sample in `fixtures/ygoprodeck_sample` is used.

On Linux it is the same, with `source .venv/bin/activate` and `export` in place of `$env:`.

## Running

```powershell
# API: POST /runs, GET /runs/{id}, GET /runs/{id}/classifications?category=, GET /listings/{id}
uvicorn imagetool.main:create_app --factory --reload
# then open http://127.0.0.1:8000/docs

# One Run from the command line
python -m imagetool.cli run specs/example.yaml

# Score against the fixtures (pass bar 80 %, D12)
python -m imagetool.cli benchmark
```

Settings (environment variables):

| Variable | Default | Meaning |
|----------|---------|---------|
| `IMAGETOOL_DATA_DIR` | `./data` | SQLite file + 512 px image copies |
| `IMAGETOOL_DATABASE` | `<data>/imagetool.db` | SQLite path |
| `IMAGETOOL_OCR` | `fixture` | `fixture` \| `tesseract` \| `none` |
| `IMAGETOOL_IMAGE_CLASSIFIER` | `fixture` | `fixture` \| `clip` \| `none` |
| `IMAGETOOL_TESSERACT_CMD` | — | Path to `tesseract.exe` |
| `IMAGETOOL_CLIP_MODEL` | `ViT-B-32/laion2b_s34b_b79k` | `<architecture>/<pretrained>` |
| `IMAGETOOL_THUMBNAIL_SIZE` | `512` | Long edge of the stored copy |

## Run Spec

```yaml
source: mock_marketplace
query: "yu-gi-oh"                  # optional
categories: [yugioh_card, vinyl]   # default: all four; others can never win
countries: [GR, HR, BG, RO, EE]
price: {min: 0, max: 200, currency: EUR}
posted_after: 2026-10-01
max_listings: 100
min_confidence: 0.6                # below → unknown (signals are still stored)
```

## What the benchmark does and doesn't tell you

`benchmark` runs on the mock fixtures with the fixture engines. The fixture OCR text is
hand-written to look like noisy real OCR (`WH1TE DRAGCN`, `LOB-EN1l9`), so the benchmark
measures the **rules, dictionaries and catalog matching**. It does not measure how well
Tesseract or CLIP read real photos. The fixtures were written together with the rules, so
100 % here is a regression check, not proof of real-world accuracy. Real accuracy needs
real listings with labelled answers.
