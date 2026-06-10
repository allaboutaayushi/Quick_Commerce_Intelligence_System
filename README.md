# RevQ Take-Home Exercise Submission

A small slice of a quick-commerce brand intelligence system: canonical product identity, SQLite ingestion, and a React product detail page backed by a tiny Express API.

## Requirements

- Python 3.10+
- Node.js 18+
- `sqlite3` CLI available on PATH

## Run

```bash
# 1. Build the SQLite database from the sample scrapes
cd ingest
rm -f revq.db revq.db-shm revq.db-wal
python3 ingest.py ../data/blinkit_sample.json
python3 ingest.py ../data/zepto_sample.json
python3 ingest.py ../data/instamart_sample.json

# 2. Start the app
cd ../app
npm install
npm run dev
```

Open `http://localhost:5180/product/1`. The API runs on `http://localhost:3001` and Vite proxies `/api` to it. The dev server uses a strict port (5180) so it fails loudly instead of silently moving to another port when something else is already listening. I used the local `sqlite3` CLI from the Express server to avoid native Node SQLite compilation issues.

## Cross-platform product identity

I modelled a real-world SKU in `products` and each platform-specific listing in `platform_listings`. During ingest, each scraped item is normalised into a `canonical_key` built from product type, flavour/variant, and grams: for example `protein_bar__chocolate_chunk_nuts__60`.

The matching is deliberately explainable. Weight parsing handles grams, kilograms, and pack formats like `6x60g` or `38g x 6`. Product type and flavour are detected with ordered substring rules, with more specific variants checked first. That makes the judgement calls visible in code and in `schema.md`.

What breaks it: renamed products with new flavour words, ambiguous bundles where total grams are the same but pack count differs, and close variants like Instamart's `Almond + Cashew Crunch` versus other platforms' `Almond Crunch`. In production I would keep this deterministic key as the first pass, then add human-reviewed mappings and confidence scoring for low-confidence matches.

One source-data note: the Instamart sample's Unix timestamp converts to April 28, 2024, while Blinkit and Zepto are dated April 28, 2026. I preserved the source timestamp instead of rewriting it during ingest.

## Component tree

```text
App
└── ProductDetail
    ├── ProductHeader
    ├── PriceTable
    └── AvailabilitySection
```

`ProductDetail` owns the route-level fetch through `useProduct` and passes plain props down. The child components are split by the business questions on the page: what product is this, how does price compare, and where is it live. Loading, empty, and error states stay at the page boundary so the display components can stay simple.

## Where state lives

Server-side state lives in SQLite because the main modelling problem is canonical mapping plus time-series price and availability. The Express API reads the latest snapshots, calculates discount, and returns one product-shaped response for the UI.

Client state is local to `useProduct(id)`: `loading | success | empty | error`. I did not add a global store because this app has one required route and no shared mutable UI state.

## What's fragile or unfinished

- The matching rules are hand-written for this Yogabar sample set. They are auditable, but they will miss unfamiliar naming patterns.
- Pack count is not stored separately, so a hypothetical single 360g product could collide with a 6x60g pack.
- The product page shows current price and availability only. The schema supports 30-day history and the query is documented in `schema.sql`, but I did not add a chart.
- The API is intentionally small: no auth, pagination, or observability.
- The server shells out to `sqlite3`, which is acceptable for this local exercise but not what I would ship in production.

## Next 4 hours

First I would add match confidence and a small review table for product identity, because wrong identity pollutes every downstream metric. Next I would add `latest_price_snapshots` and `latest_availability_snapshots` materialisations so the API does not repeatedly run latest-row subqueries. After that I would add a price-history endpoint and tests around the parser fixtures and API response shape.

## Questions I would ask

- Should `Almond Crunch Muesli` and `Almond + Cashew Crunch Muesli` be treated as the same SKU or separate variants? I treated them as separate.
- Do platform prices arrive in paise or rupees in production? The sample looks like rupees, so I stored integer rupees for this exercise.
