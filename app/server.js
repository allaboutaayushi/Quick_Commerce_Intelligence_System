import express from "express";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { existsSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "../ingest/revq.db");
const PORT = process.env.PORT || 3001;

if (!existsSync(DB_PATH)) {
  console.error(`Database not found at ${DB_PATH}`);
  console.error("Run the ingest script first from ../ingest.");
  process.exit(1);
}

const app = express();
app.use(express.json());

function query(sql) {
  const output = execFileSync("sqlite3", ["-json", DB_PATH, sql], { encoding: "utf8" });
  return output.trim() ? JSON.parse(output) : [];
}

app.get("/api/products", (_req, res) => {
  try {
    const rows = query(`
      SELECT
        p.id,
        p.canonical_name,
        p.brand,
        p.weight_g,
        p.category,
        (SELECT pl.image_url
         FROM platform_listings pl
         WHERE pl.product_id = p.id AND pl.image_url IS NOT NULL
         LIMIT 1) AS image_url
      FROM products p
      ORDER BY p.category, p.canonical_name
    `);
    res.json(rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get("/api/products/:id", (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: "Invalid id" });
  }

  try {
    const [product] = query(`SELECT * FROM products WHERE id = ${id}`);
    if (!product) return res.status(404).json({ error: "Product not found" });

    const listings = query(`
      SELECT
        pl.id AS listing_id,
        pl.platform,
        pl.platform_name,
        pl.image_url,
        ps.mrp,
        ps.selling_price,
        ps.scraped_at
      FROM platform_listings pl
      LEFT JOIN price_snapshots ps
        ON ps.listing_id = pl.id
        AND ps.scraped_at = (
          SELECT MAX(scraped_at) FROM price_snapshots WHERE listing_id = pl.id
        )
      WHERE pl.product_id = ${id}
      ORDER BY CASE pl.platform
        WHEN 'blinkit' THEN 1
        WHEN 'zepto' THEN 2
        WHEN 'instamart' THEN 3
        ELSE 4
      END
    `);

    const platforms = listings.map((listing) => {
      const availability = query(`
        SELECT pincode, in_stock
        FROM availability_snapshots
        WHERE listing_id = ${listing.listing_id}
          AND scraped_at = (
            SELECT MAX(scraped_at)
            FROM availability_snapshots
            WHERE listing_id = ${listing.listing_id}
          )
        ORDER BY pincode
      `);

      const total = availability.length;
      const live = availability.filter((row) => row.in_stock === 1).length;
      const oosPincodes = availability
        .filter((row) => row.in_stock === 0)
        .map((row) => row.pincode);
      const discountPct = listing.mrp && listing.selling_price
        ? Math.round(((listing.mrp - listing.selling_price) / listing.mrp) * 100)
        : null;

      return {
        platform: listing.platform,
        platform_name: listing.platform_name,
        image_url: listing.image_url,
        mrp: listing.mrp,
        selling_price: listing.selling_price,
        discount_pct: discountPct,
        scraped_at: listing.scraped_at,
        live_pincodes: live,
        total_pincodes: total,
        oos_pincodes: oosPincodes,
      };
    });

    const image_url = platforms.find((platform) => platform.image_url)?.image_url ?? null;
    res.json({ ...product, image_url, platforms });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const DIST = join(__dirname, "dist");
if (existsSync(DIST)) {
  app.use(express.static(DIST));
  app.get("*", (_req, res) => res.sendFile(join(DIST, "index.html")));
}

const server = app.listen(PORT, () => {
  console.log(`API server -> http://localhost:${PORT}`);
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`Port ${PORT} is already in use. Stop the other process (lsof -ti:${PORT} | xargs kill) and retry.`);
    process.exit(1);
  }
  throw err;
});
