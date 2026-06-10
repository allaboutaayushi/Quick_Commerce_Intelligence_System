-- Cross-platform canonical product identity.
-- One row here represents the real-world product (e.g. "Yogabar CCN Protein Bar 60g"),
-- independent of how any platform names or IDs it.
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    brand           TEXT    NOT NULL,
    canonical_name  TEXT    NOT NULL,
    canonical_key   TEXT    NOT NULL UNIQUE,
    category        TEXT,
    weight_g        REAL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Stable per-product, per-platform identity.
-- Each platform has its own ID format and naming, stored raw here.
-- image_url is the most recent image seen for this listing.
CREATE TABLE IF NOT EXISTS platform_listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          INTEGER NOT NULL REFERENCES products(id),
    platform            TEXT    NOT NULL CHECK (platform IN ('blinkit', 'zepto', 'instamart')),
    platform_product_id TEXT    NOT NULL,
    platform_name       TEXT    NOT NULL,
    image_url           TEXT,
    UNIQUE (platform, platform_product_id)
);

-- Append-only price snapshots. One row per (listing, scrape run).
-- Supports current price and 30-day history queries without schema changes.
CREATE TABLE IF NOT EXISTS price_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id    INTEGER NOT NULL REFERENCES platform_listings(id),
    scraped_at    TEXT    NOT NULL,
    mrp           INTEGER NOT NULL,
    selling_price INTEGER NOT NULL,
    UNIQUE (listing_id, scraped_at)
);

-- Append-only availability snapshots. One row per (listing, pincode, scrape run).
-- Separating this from price_snapshots avoids a wide denormalized row and lets
-- pincode sets differ across platforms and over time.
CREATE TABLE IF NOT EXISTS availability_snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES platform_listings(id),
    scraped_at TEXT    NOT NULL,
    pincode    TEXT    NOT NULL,
    in_stock   INTEGER NOT NULL CHECK (in_stock IN (0, 1)),
    UNIQUE (listing_id, scraped_at, pincode)
);

-- ---- Indexes ----

-- Canonical matching during ingest is a direct lookup, not name search.
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_canonical_key ON products(canonical_key);

-- Most reads start from products; listing lookups come second.
CREATE INDEX IF NOT EXISTS idx_listings_product ON platform_listings(product_id);

-- Price history is always scoped to a listing, ordered by time.
CREATE INDEX IF NOT EXISTS idx_price_listing_time ON price_snapshots(listing_id, scraped_at DESC);

-- Availability queries filter by listing + time, then optionally by in_stock.
CREATE INDEX IF NOT EXISTS idx_avail_listing_time ON availability_snapshots(listing_id, scraped_at DESC);

-- ---- Query reference ----

-- Q1: Current price of Product X on all 3 platforms
-- SELECT pl.platform, ps.mrp, ps.selling_price, ps.scraped_at
-- FROM platform_listings pl
-- JOIN price_snapshots ps ON ps.listing_id = pl.id
--   AND ps.scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots WHERE listing_id = pl.id)
-- WHERE pl.product_id = ?;

-- Q2: 30-day price history of Product X on Blinkit
-- SELECT ps.selling_price, ps.mrp, ps.scraped_at
-- FROM platform_listings pl
-- JOIN price_snapshots ps ON ps.listing_id = pl.id
-- WHERE pl.product_id = ? AND pl.platform = 'blinkit'
--   AND ps.scraped_at >= datetime('now', '-30 days')
-- ORDER BY ps.scraped_at;

-- Q3: Pincodes where Product X is out of stock, per platform
-- SELECT pl.platform, av.pincode
-- FROM platform_listings pl
-- JOIN availability_snapshots av ON av.listing_id = pl.id
--   AND av.scraped_at = (SELECT MAX(scraped_at) FROM availability_snapshots WHERE listing_id = pl.id)
-- WHERE pl.product_id = ? AND av.in_stock = 0;
