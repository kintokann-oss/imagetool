CREATE TABLE runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_json         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',   -- pending | running | done | failed
    started_at        TEXT,
    finished_at       TEXT,
    fetched           INTEGER NOT NULL DEFAULT 0,
    skipped_unchanged INTEGER NOT NULL DEFAULT 0,
    classified        INTEGER NOT NULL DEFAULT 0,
    unknown           INTEGER NOT NULL DEFAULT 0,
    failed            INTEGER NOT NULL DEFAULT 0,
    error             TEXT
);

CREATE TABLE listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,
    source_listing_id   TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    price               REAL,
    currency            TEXT NOT NULL DEFAULT 'EUR',
    country             TEXT,
    posted_at           TEXT,
    source_url          TEXT NOT NULL DEFAULT '',
    language            TEXT,
    raw_attributes_json TEXT NOT NULL DEFAULT '{}',
    content_hash        TEXT NOT NULL,
    first_seen_run_id   INTEGER REFERENCES runs(id),
    last_seen_run_id    INTEGER REFERENCES runs(id),
    UNIQUE (source, source_listing_id)
);

CREATE TABLE listing_prices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    run_id     INTEGER NOT NULL REFERENCES runs(id),
    price      REAL,
    currency   TEXT NOT NULL
);

-- One row per image: 512 px copy + URL + raw OCR text (D14, D16).
CREATE TABLE listing_images (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id           INTEGER NOT NULL REFERENCES listings(id),
    position             INTEGER NOT NULL,
    source_url           TEXT NOT NULL,
    thumbnail_path       TEXT,
    ocr_text             TEXT NOT NULL DEFAULT '',
    ocr_lines_json       TEXT NOT NULL DEFAULT '[]',
    category_scores_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (listing_id, position)
);

CREATE TABLE classifications (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id           INTEGER NOT NULL REFERENCES listings(id),
    run_id               INTEGER NOT NULL REFERENCES runs(id),
    category             TEXT NOT NULL,
    confidence           REAL NOT NULL,
    is_bundle            INTEGER NOT NULL DEFAULT 0,
    estimated_item_count INTEGER,
    identity_json        TEXT NOT NULL DEFAULT '{}',
    created_at           TEXT NOT NULL
);
CREATE INDEX idx_classifications_run ON classifications(run_id, category);
CREATE INDEX idx_classifications_listing ON classifications(listing_id);

CREATE TABLE signals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    classification_id INTEGER NOT NULL REFERENCES classifications(id),
    kind              TEXT NOT NULL,
    category          TEXT NOT NULL,
    weight            REAL NOT NULL,
    detail            TEXT NOT NULL
);
CREATE INDEX idx_signals_classification ON signals(classification_id);
