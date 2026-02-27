-- 001_create_enriched_market_data.sql
-- Table principale : output du Spark stream-to-stream join

CREATE TABLE IF NOT EXISTS enriched_market_data (
    id                      BIGSERIAL       PRIMARY KEY,
    symbol                  VARCHAR(20)     NOT NULL,
    window_start            TIMESTAMPTZ     NOT NULL,
    window_end              TIMESTAMPTZ     NOT NULL,
    open_price              NUMERIC(18, 8),
    close_price             NUMERIC(18, 8),
    high_price              NUMERIC(18, 8),
    low_price               NUMERIC(18, 8),
    avg_price               NUMERIC(18, 8),
    total_volume            NUMERIC(28, 8),
    trade_count             INTEGER,
    price_change_pct        NUMERIC(10, 4),
    volatility_score        NUMERIC(6, 4),
    is_spike                BOOLEAN         DEFAULT FALSE,
    related_article_url     TEXT,
    fred_interest_rate      NUMERIC(8, 4),
    fred_inflation_rate     NUMERIC(8, 4),
    enriched_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_enriched_window UNIQUE (symbol, window_start)
);

CREATE INDEX idx_enriched_symbol       ON enriched_market_data (symbol);
CREATE INDEX idx_enriched_window_start ON enriched_market_data (window_start DESC);
CREATE INDEX idx_enriched_is_spike     ON enriched_market_data (is_spike) WHERE is_spike = TRUE;

