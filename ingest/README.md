# Ingest

## Requirements

Python 3.10+. No third-party packages are required.

## Run

```bash
cd ingest

# Optional if you want a clean rebuild
rm -f revq.db revq.db-shm revq.db-wal

python3 ingest.py ../data/blinkit_sample.json
python3 ingest.py ../data/zepto_sample.json
python3 ingest.py ../data/instamart_sample.json
```

The SQLite database is written to `ingest/revq.db`. Re-running the same file is idempotent for price and availability snapshots with the same scrape timestamp.

## What it does

1. Detects which platform produced the JSON.
2. Normalises product weight, product type, and flavour/variant.
3. Resolves a canonical product through `products.canonical_key`.
4. Upserts the platform listing and writes price and availability snapshots.
