# Schema Design Notes

## 1. Cross-platform product identity

**How it works**

A `products` row represents the real-world product — independent of platform. Each platform gets a `platform_listings` row linked to that canonical product. The link is established at ingest time by a normalisation + matching step:

1. **Weight normalisation** — parse weight to grams from wildly different formats (`60 g`, `60GM`, `0.36 kg`, `6X60GM`, `38g x 6`, `1000g`).
2. **Product-type detection** — classify into buckets (`protein_bar`, `energy_bar`, `muesli`, `cereal`, `peanut_butter`, `oats`) via substring matching, most-specific pattern first.
3. **Flavour detection** — match longest/most-specific keyword first (`dark_chocolate_cranberry` before `cranberry`, `peanut_butter_chocolate` before `peanut_butter`, etc.).
4. **Canonical key** — `{product_type}__{flavour}__{weight_g}`. If a row with this key already exists in `products`, the new listing is linked to it. Otherwise a new canonical product is created.

**Judgment calls in the sample data**

| Situation | Decision | Rationale |
|---|---|---|
| Blinkit "21g Protein Bar Double Cocoa" vs Zepto "20G Protein Bar Double Cocoa" | Same product | MRP ₹720, same pack size, same flavour; "21g/20g" is a naming discrepancy, not a different SKU. |
| Blinkit/Zepto "Almond Crunch Muesli" vs Instamart "Almond + Cashew Crunch Muesli" | Different products | Ingredient list differs (almond-only vs almond+cashew); image slugs differ; selling price differs. Treated as distinct canonical products. |
| Instamart `weight_unit: "kg"` with value `"0.36"` | 360 g | Normalised at parse time. |
| Instamart `snapshot_time` resolves to 2024 while other files are 2026 | Preserve source timestamp | I did not rewrite source data during ingest. |

**What this approach breaks on**

- **Renamed products**: if a platform renames a product (new flavour, reformulation), ingest creates a duplicate canonical product. The key is purely structural — there's no name-similarity fallback.
- **Bundle vs component confusion**: "Pack of 6 × 60g = 360g" and a hypothetical "360g single bar" would get the same key. Weight alone isn't enough — you'd need to add pack count to the key, which requires reliable extraction.
- **Instamart's Almond+Cashew ambiguity**: my call could be wrong. If those _are_ the same product, they'd be misidentified as separate, and cross-platform pricing would look incomplete for both.
- **SKU proliferation at scale**: as brands add more variants, false negatives (missed matches) accumulate. The right production solution is to bootstrap with this heuristic and layer in human-curated golden pairs + an ML similarity model trained on those pairs.

---

## 2. One denormalisation / one index for scale

**Indexes**: `idx_products_canonical_key ON products(canonical_key)` and `idx_price_listing_time ON price_snapshots(listing_id, scraped_at DESC)`

The canonical-key index makes ingest matching a direct lookup instead of a name scan. The snapshot uniqueness constraints keep re-runs idempotent at the database layer. Every price read then starts with "give me the latest snapshot for this listing", which is a range scan over `(listing_id, scraped_at)`. Without the price index, every current-price query is a full-table scan over what could be millions of snapshot rows.

**Denormalisation I'd consider**: materialise a `latest_price_snapshots` table (or a covering view backed by a scheduled job) that stores only the most recent price row per listing. This turns the "get current price" path from a correlated subquery into a direct lookup, and removes repeated `MAX(scraped_at)` subqueries. The trade-off is write amplification (two writes per scrape instead of one) and the risk of staleness if the job lags.

---

## 3. What changes at 100× scrape volume

At 100× volume, the main bottlenecks are:

1. **`availability_snapshots` write throughput** — this table grows fastest (products × pincodes × scrape frequency). At that scale I'd partition it by date in Postgres, or move it to a columnar store (ClickHouse, BigQuery) where append-heavy time-series queries are cheaper.
2. **"Latest snapshot" queries become expensive** — even with the index, `MAX(scraped_at)` subqueries on millions of rows hurt. The materialised `latest_price_snapshots` table above becomes non-optional.
3. **Canonical matching is a bottleneck** — right now matching runs in Python at ingest time. At 100× you'd decouple scrape → raw storage and matching → canonical mapping into separate async workers, with a queue in between.
4. **SQLite can't handle concurrent writes** — you'd move to Postgres with a write queue or connection pool.
