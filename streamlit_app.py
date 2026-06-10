"""Streamlit mirror of the product detail page, for Streamlit Community Cloud.

Builds the SQLite database from the sample scrapes on first run (the cloud
filesystem is ephemeral), then renders price comparison and availability
per canonical product. The React + Express app in app/ is the primary UI.
"""

import sqlite3
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
DB_PATH = ROOT / "ingest" / "revq.db"
DATA_FILES = [
    ROOT / "data" / "blinkit_sample.json",
    ROOT / "data" / "zepto_sample.json",
    ROOT / "data" / "instamart_sample.json",
]

PLATFORM_LABELS = {"blinkit": "Blinkit", "zepto": "Zepto", "instamart": "Instamart"}
PLATFORM_ORDER = ["blinkit", "zepto", "instamart"]

_CSS = """
<style>
h1 { font-size: 1.6rem; letter-spacing: -0.01em; }
.stMarkdown h3 { font-size: 0.85rem !important; text-transform: uppercase;
     letter-spacing: 0.08em; color: #6b7280 !important; font-weight: 600;
     padding-bottom: 0; }
.product-title { font-size: 1.25rem; font-weight: 600; margin: 0.25rem 0 0; }
.brand-label { color: #6b7280; font-size: 0.8rem; text-transform: uppercase;
               letter-spacing: 0.08em; }
.avail-row { padding: 0.7rem 0; border-bottom: 1px solid #e5e7eb; }
.avail-row:last-child { border-bottom: none; }
.platform-name { font-weight: 600; }
.status-live { color: #15803d; }
.status-partial { color: #b45309; }
.status-out { color: #b91c1c; }
.status-unlisted { color: #9ca3af; }
.row-meta { color: #9ca3af; font-size: 0.78rem; margin-top: 0.15rem; }
</style>
"""


@st.cache_resource
def ensure_db() -> str:
    if not DB_PATH.exists():
        sys.path.insert(0, str(ROOT / "ingest"))
        from ingest import ingest

        for data_file in DATA_FILES:
            ingest(data_file)
    return str(DB_PATH)


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(ensure_db())
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


st.set_page_config(page_title="Quick-Commerce Brand Intelligence", layout="centered")
st.markdown(_CSS, unsafe_allow_html=True)

st.title("Quick-Commerce Brand Intelligence")
st.caption(
    "Cross-platform product identity, pricing, and availability for Yogabar "
    "across Blinkit, Zepto, and Instamart."
)

products = query("SELECT id, canonical_name, brand FROM products ORDER BY category, canonical_name")
if not products:
    st.error("No products found in the database.")
    st.stop()

selected = st.selectbox(
    "Product",
    products,
    format_func=lambda p: p["canonical_name"],
)

listings = query(
    """
    SELECT pl.id AS listing_id, pl.platform, pl.platform_name, ps.mrp, ps.selling_price, ps.scraped_at
    FROM platform_listings pl
    LEFT JOIN price_snapshots ps
      ON ps.listing_id = pl.id
      AND ps.scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots WHERE listing_id = pl.id)
    WHERE pl.product_id = ?
    """,
    (selected["id"],),
)
by_platform = {row["platform"]: row for row in listings}

st.markdown(
    f"<p class='brand-label'>{selected['brand']}</p>"
    f"<p class='product-title'>{selected['canonical_name']}</p>",
    unsafe_allow_html=True,
)
st.divider()

st.markdown("### Price comparison")
price_rows = []
for platform in PLATFORM_ORDER:
    row = by_platform.get(platform)
    if row and row["selling_price"] is not None:
        discount = round((row["mrp"] - row["selling_price"]) / row["mrp"] * 100) if row["mrp"] else None
        price_rows.append({
            "Platform": PLATFORM_LABELS[platform],
            "Selling price": f"₹{row['selling_price']}",
            "MRP": f"₹{row['mrp']}",
            "Discount": f"{discount}%" if discount is not None else "—",
        })
    else:
        price_rows.append({
            "Platform": PLATFORM_LABELS[platform],
            "Selling price": "Not listed",
            "MRP": "—",
            "Discount": "—",
        })
st.table(price_rows)

st.markdown("### Availability by pincode")
for platform in PLATFORM_ORDER:
    row = by_platform.get(platform)
    if not row:
        st.markdown(
            f"<div class='avail-row'><span class='platform-name'>{PLATFORM_LABELS[platform]}</span>"
            f" <span class='status-unlisted'>· Not listed on this platform</span></div>",
            unsafe_allow_html=True,
        )
        continue

    availability = query(
        """
        SELECT pincode, in_stock
        FROM availability_snapshots
        WHERE listing_id = ?
          AND scraped_at = (SELECT MAX(scraped_at) FROM availability_snapshots WHERE listing_id = ?)
        ORDER BY pincode
        """,
        (row["listing_id"], row["listing_id"]),
    )
    total = len(availability)
    live = sum(1 for a in availability if a["in_stock"] == 1)
    oos = [a["pincode"] for a in availability if a["in_stock"] == 0]

    if total > 0 and live == total:
        status = f"<span class='status-live'>Live in {live} of {total} pincodes</span>"
    elif live == 0:
        status = f"<span class='status-out'>Out of stock in all {total} pincodes</span>"
    else:
        status = (
            f"<span class='status-partial'>Live in {live} of {total} pincodes"
            f" · out of stock: {', '.join(oos)}</span>"
        )

    st.markdown(
        f"<div class='avail-row'>"
        f"<span class='platform-name'>{PLATFORM_LABELS[platform]}</span> · {status}"
        f"<div class='row-meta'>Listed as “{row['platform_name']}”"
        f" · last scraped {row['scraped_at'] or 'never'}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
