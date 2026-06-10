#!/usr/bin/env python3
"""
ingest.py  —  Read one of the three platform JSON files, resolve cross-platform
product identity, and upsert into SQLite.

Usage:
    python3 ingest.py <path-to-json>

Run for all three to fully populate the DB:
    python3 ingest.py ../data/blinkit_sample.json
    python3 ingest.py ../data/zepto_sample.json
    python3 ingest.py ../data/instamart_sample.json
"""

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "revq.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


# ---------------------------------------------------------------------------
# Weight normalisation
# ---------------------------------------------------------------------------

def extract_weight_g(text: str, raw_weight=None, weight_unit: str | None = None) -> float | None:
    """Return weight in grams, or None if unparseable."""
    if raw_weight is not None and weight_unit is not None:
        w = float(raw_weight)
        return round(w * 1000 if weight_unit == "kg" else w, 2)

    t = text.lower()
    # Strip "21g protein" / "20g protein" — that's protein content, not product weight.
    t = re.sub(r"\d+\s*g\s+protein", "", t)
    # "6 x 60g", "6x60gm", "38g x 6", "6 x 38 g"
    m = re.search(r"(\d+)\s*[xX×]\s*(\d+)\s*g", t)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.search(r"(\d+)\s*g\s*[xX×]\s*(\d+)", t)
    if m:
        return int(m.group(1)) * int(m.group(2))
    # "1 kg", "1.5 kg"
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg", t)
    if m:
        return round(float(m.group(1)) * 1000)
    # "400g", "400 gm", "400gms", "228GM"
    m = re.search(r"(\d+)\s*g(?:m(?:s)?)?(?:\b|$)", t)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Product-type detection (most-specific patterns first)
# ---------------------------------------------------------------------------

_PRODUCT_TYPE_PATTERNS = [
    ("protein_bar_variety", ["variety pack", "variety"]),
    ("protein_bar_21g", ["21g protein", "20g protein", "21 g protein", "20 g protein"]),
    ("protein_bar", ["protein bar"]),
    ("energy_bar", ["energy bar", "multigrain energy", "multigrain bar", "multi grain bar"]),
    ("muesli", ["muesli"]),
    ("cereal", ["breakfast cereal", "wholegrain cereal", "wholegrain breakfast", "cereal"]),
    ("peanut_butter", ["peanut butter"]),
    ("oats", ["rolled oats", "oats"]),
]

def detect_product_type(text: str, flavour: str = "") -> str:
    # These flavours only appear in protein bars. Use flavour as a tiebreaker
    # so abbreviated names like "CHOC CHUNK NUTS BAR" aren't misclassified.
    _PROTEIN_BAR_FLAVOURS = {"chocolate_chunk_nuts", "peanut_butter_chocolate", "almond_fudge", "double_cocoa"}
    if flavour in _PROTEIN_BAR_FLAVOURS:
        t = text.lower()
        if re.search(r"(?<!\d)2[01]\s*g\s+protein|(?<!\d)2[01]\s*g\b.*protein", t):
            return "protein_bar_21g"
        return "protein_bar"

    t = text.lower()
    for ptype, patterns in _PRODUCT_TYPE_PATTERNS:
        if any(p in t for p in patterns):
            return ptype
    return "unknown"


# ---------------------------------------------------------------------------
# Flavour detection (most-specific patterns first)
# ---------------------------------------------------------------------------

_FLAVOUR_PATTERNS = [
    ("chocolate_chunk_nuts",      ["chocolate chunk & nuts", "chocolate chunk nuts", "choc chunk nuts", "ccn"]),
    ("peanut_butter_chocolate",   ["peanut butter choc", "peanut butter chocolate", "pbc"]),
    ("almond_fudge",              ["almond fudge", "alf"]),
    ("double_cocoa",              ["double cocoa", "dcoc"]),
    ("dark_chocolate_cranberry",  ["dark choc cranberry", "dark chocolate cranberry", "dark choc & cranberry",
                                   "dark chocolate & cranberry", "dccran", "dccr"]),
    ("cranberry",                 ["cranberry", "cran"]),
    ("mango",                     ["mango"]),
    ("almond_cashew_crunch",      ["almond + cashew crunch", "almond cashew crunch", "almond + cashew",
                                   "almond cashew"]),
    ("almond_crunch",             ["almond crunch"]),
    ("choco_almond",              ["choco almond", "chocolate almond"]),
    ("dark_chocolate",            ["dark chocolate", "dark choc"]),
    ("crunchy",                   ["crunchy"]),
    ("smooth",                    ["smooth"]),
]

def detect_flavour(text: str) -> str:
    t = text.lower()
    for flavour, patterns in _FLAVOUR_PATTERNS:
        if any(p in t for p in patterns):
            return flavour
    return "none"


# ---------------------------------------------------------------------------
# Canonical name / category helpers
# ---------------------------------------------------------------------------

_TYPE_LABELS = {
    "protein_bar":         "Protein Bar",
    "protein_bar_21g":     "21g Protein Bar",
    "protein_bar_variety": "Protein Bar Variety Pack",
    "energy_bar":          "Multigrain Energy Bar",
    "muesli":              "Muesli",
    "cereal":              "Breakfast Cereal",
    "peanut_butter":       "Peanut Butter",
    "oats":                "Rolled Oats",
    "unknown":             "Product",
}

_FLAVOUR_LABELS = {
    "chocolate_chunk_nuts":     "Chocolate Chunk & Nuts",
    "peanut_butter_chocolate":  "Peanut Butter Chocolate",
    "almond_fudge":             "Almond Fudge",
    "double_cocoa":             "Double Cocoa",
    "dark_chocolate_cranberry": "Dark Chocolate & Cranberry",
    "cranberry":                "Cranberry",
    "mango":                    "Mango",
    "almond_cashew_crunch":     "Almond + Cashew Crunch",
    "almond_crunch":            "Almond Crunch",
    "choco_almond":             "Choco Almond",
    "dark_chocolate":           "Dark Chocolate",
    "crunchy":                  "Crunchy",
    "smooth":                   "Smooth",
    "none":                     "",
}

_TYPE_CATEGORY = {
    "protein_bar":         "Health Foods > Protein Bars",
    "protein_bar_21g":     "Health Foods > Protein Bars",
    "protein_bar_variety": "Health Foods > Protein Bars",
    "energy_bar":          "Health Foods > Energy Bars",
    "muesli":              "Breakfast > Muesli & Granola",
    "cereal":              "Breakfast > Cereals",
    "peanut_butter":       "Spreads > Peanut Butter",
    "oats":                "Breakfast > Oats",
    "unknown":             "Other",
}


def make_canonical_name(brand: str, product_type: str, flavour: str, weight_g: float | None) -> str:
    parts = [brand]
    fl = _FLAVOUR_LABELS.get(flavour, "")
    if fl:
        parts.append(fl)
    parts.append(_TYPE_LABELS.get(product_type, product_type))
    if weight_g:
        w = int(weight_g) if weight_g == int(weight_g) else weight_g
        parts.append(f"({w}g)")
    return " ".join(parts)


def make_canonical_key(product_type: str, flavour: str, weight_g: float | None) -> str:
    if weight_g is None:
        weight_part = "unknown"
    elif float(weight_g).is_integer():
        weight_part = str(int(weight_g))
    else:
        weight_part = str(weight_g)
    return f"{product_type}__{flavour}__{weight_part}"


# ---------------------------------------------------------------------------
# Platform-specific parsers
# ---------------------------------------------------------------------------

def parse_blinkit(raw: dict) -> tuple[str, list[dict]]:
    scraped_at = raw["scraped_at"]
    brand = raw["brand"]
    products = []
    for item in raw["products"]:
        name = item["name"]
        weight_g = extract_weight_g(name)
        products.append({
            "brand": brand,
            "platform_product_id": item["blinkit_id"],
            "platform_name": name,
            "mrp": item["mrp"],
            "selling_price": item["selling_price"],
            "image_url": item.get("image_url"),
            "scraped_at": scraped_at,
            "weight_g": weight_g,
            "product_type": detect_product_type(name, detect_flavour(name)),
            "flavour": detect_flavour(name),
            "availability": [
                {"pincode": a["pincode"], "in_stock": 1 if a["in_stock"] else 0}
                for a in item.get("availability", [])
            ],
        })
    return "blinkit", products


def parse_zepto(raw: dict) -> tuple[str, list[dict]]:
    scraped_at = raw["fetched_on"] + "T00:00:00Z"
    products = []
    for item in raw["items"]:
        name = item["title"]
        weight_g = extract_weight_g(name)
        flavour = detect_flavour(name)
        products.append({
            "brand": "Yogabar",
            "platform_product_id": item["sku_code"],
            "platform_name": name,
            "mrp": item["price"]["mrp"],
            "selling_price": item["price"]["final"],
            "image_url": item.get("image"),
            "scraped_at": scraped_at,
            "weight_g": weight_g,
            "product_type": detect_product_type(name, flavour),
            "flavour": flavour,
            "availability": [
                {"pincode": pin, "in_stock": 1 if status == "available" else 0}
                for pin, status in item.get("stock_by_pincode", {}).items()
            ],
        })
    return "zepto", products


def parse_instamart(raw: dict) -> tuple[str, list[dict]]:
    ts = int(raw["snapshot_time"])
    scraped_at = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    products = []
    for item in raw["results"]:
        name = item["display_name"]
        weight_g = extract_weight_g(
            name,
            raw_weight=item.get("weight"),
            weight_unit=item.get("weight_unit"),
        )
        avail = item.get("store_availability", [])
        availability = [
            {"pincode": a["pin"], "in_stock": 1 if a["available_qty"] > 0 else 0}
            for a in avail
        ]
        products.append({
            "brand": "Yogabar",
            "platform_product_id": item["product_id"],
            "platform_name": name,
            "mrp": item["store_mrp"],
            "selling_price": item["store_selling_price"],
            "image_url": item.get("image"),
            "scraped_at": scraped_at,
            "weight_g": weight_g,
            "product_type": detect_product_type(name, detect_flavour(name)),
            "flavour": detect_flavour(name),
            "availability": availability,
        })
    return "instamart", products


_PARSERS = {
    "platform": parse_blinkit,       # blinkit root key
    "source": parse_zepto,           # zepto root key
    "platform_name": parse_instamart, # instamart root key
}


def detect_and_parse(raw: dict) -> tuple[str, list[dict]]:
    for key, parser in _PARSERS.items():
        if key in raw:
            return parser(raw)
    raise ValueError("Unknown JSON format — could not detect platform")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def upsert_canonical_product(conn: sqlite3.Connection, brand: str, product_type: str,
                              flavour: str, weight_g: float | None) -> int:
    key = make_canonical_key(product_type, flavour, weight_g)
    row = conn.execute(
        "SELECT id FROM products WHERE canonical_key = ?",
        (key,),
    ).fetchone()
    if row:
        return row[0]

    canonical_name = make_canonical_name(brand, product_type, flavour, weight_g)
    category = _TYPE_CATEGORY.get(product_type, "Other")
    cur = conn.execute(
        """INSERT INTO products (brand, canonical_name, canonical_key, category, weight_g)
           VALUES (?, ?, ?, ?, ?)""",
        (brand, canonical_name, key, category, weight_g),
    )
    return cur.lastrowid


def upsert_listing(conn: sqlite3.Connection, product_id: int, platform: str,
                   platform_product_id: str, platform_name: str, image_url: str | None) -> int:
    conn.execute(
        """INSERT INTO platform_listings (product_id, platform, platform_product_id, platform_name, image_url)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(platform, platform_product_id)
           DO UPDATE SET platform_name=excluded.platform_name,
                         image_url=COALESCE(excluded.image_url, image_url)""",
        (product_id, platform, platform_product_id, platform_name, image_url),
    )
    row = conn.execute(
        "SELECT id FROM platform_listings WHERE platform = ? AND platform_product_id = ?",
        (platform, platform_product_id),
    ).fetchone()
    return row[0]


def insert_price_snapshot(conn: sqlite3.Connection, listing_id: int, scraped_at: str,
                           mrp: int, selling_price: int) -> None:
    # Idempotent: skip if an identical row already exists for this scrape run.
    existing = conn.execute(
        "SELECT id FROM price_snapshots WHERE listing_id = ? AND scraped_at = ?",
        (listing_id, scraped_at),
    ).fetchone()
    if existing:
        return
    conn.execute(
        "INSERT OR IGNORE INTO price_snapshots (listing_id, scraped_at, mrp, selling_price) VALUES (?, ?, ?, ?)",
        (listing_id, scraped_at, mrp, selling_price),
    )


def insert_availability_snapshots(conn: sqlite3.Connection, listing_id: int,
                                   scraped_at: str, availability: list[dict]) -> None:
    existing = conn.execute(
        "SELECT 1 FROM availability_snapshots WHERE listing_id = ? AND scraped_at = ? LIMIT 1",
        (listing_id, scraped_at),
    ).fetchone()
    if existing:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO availability_snapshots (listing_id, scraped_at, pincode, in_stock) VALUES (?, ?, ?, ?)",
        [(listing_id, scraped_at, a["pincode"], a["in_stock"]) for a in availability],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest(json_path: Path) -> None:
    raw = json.loads(json_path.read_text())
    platform, products = detect_and_parse(raw)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)

    print(f"Platform: {platform}  |  Products: {len(products)}")

    for p in products:
        product_id = upsert_canonical_product(
            conn, p["brand"], p["product_type"], p["flavour"], p["weight_g"]
        )
        listing_id = upsert_listing(
            conn, product_id, platform,
            p["platform_product_id"], p["platform_name"], p["image_url"]
        )
        insert_price_snapshot(conn, listing_id, p["scraped_at"], p["mrp"], p["selling_price"])
        insert_availability_snapshots(conn, listing_id, p["scraped_at"], p["availability"])

        print(f"  [{platform_product_id_abbr(p)}] canonical_id={product_id}  "
              f"listing_id={listing_id}  weight_g={p['weight_g']}  "
              f"type={p['product_type']}  flavour={p['flavour']}")

    conn.commit()
    conn.close()
    print("Done.")


def platform_product_id_abbr(p: dict) -> str:
    pid = p["platform_product_id"]
    return pid if len(pid) <= 20 else pid[:17] + "..."


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    ingest(path)
