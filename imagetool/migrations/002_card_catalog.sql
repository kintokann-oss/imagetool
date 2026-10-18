-- Local snapshot of YGOPRODeck (D11, D15).
CREATE TABLE ygo_cards (
    id   INTEGER PRIMARY KEY,          -- YGOPRODeck / Konami passcode
    name TEXT NOT NULL                 -- English name
);

CREATE TABLE ygo_card_names (
    card_id         INTEGER NOT NULL REFERENCES ygo_cards(id),
    language        TEXT NOT NULL,     -- en | de | fr | it | pt | es
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    PRIMARY KEY (card_id, language)
);
CREATE INDEX idx_ygo_card_names_normalized ON ygo_card_names(normalized_name);

-- One row per printing; set codes are stored split so LOB-EN001 / LOB-DE001 / LOB-001 all match.
CREATE TABLE ygo_prints (
    card_id    INTEGER NOT NULL REFERENCES ygo_cards(id),
    set_prefix TEXT NOT NULL,
    number     TEXT NOT NULL,
    set_code   TEXT NOT NULL,
    set_name   TEXT NOT NULL,
    rarity     TEXT
);
CREATE INDEX idx_ygo_prints_code ON ygo_prints(set_prefix, number);

CREATE TABLE ygo_sets (
    set_prefix TEXT PRIMARY KEY,
    set_name   TEXT NOT NULL
);
