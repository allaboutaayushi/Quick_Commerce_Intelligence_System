import { useParams } from "react-router-dom";
import { useProduct } from "../hooks/useProduct.js";
import ProductHeader from "../components/ProductHeader.jsx";
import PriceTable from "../components/PriceTable.jsx";
import AvailabilitySection from "../components/AvailabilitySection.jsx";

const PLATFORM_ORDER = ["blinkit", "zepto", "instamart"];

function Section({ title, children }) {
  return (
    <section className="detail-section">
      <h2 className="section-title">{title}</h2>
      {children}
    </section>
  );
}

function LoadingSkeleton() {
  return (
    <div className="skeleton-wrap">
      <div className="skeleton skeleton-header" />
      <div className="skeleton skeleton-block" />
      <div className="skeleton skeleton-block" />
    </div>
  );
}

function withMissingPlatforms(platforms = []) {
  const byPlatform = new Map(platforms.map((platform) => [platform.platform, platform]));

  return PLATFORM_ORDER.map((platform) => {
    const row = byPlatform.get(platform);
    if (row) return { ...row, listed: true };

    return {
      platform,
      listed: false,
      platform_name: null,
      image_url: null,
      mrp: null,
      selling_price: null,
      discount_pct: null,
      scraped_at: null,
      live_pincodes: 0,
      total_pincodes: 0,
      oos_pincodes: [],
    };
  });
}

export default function ProductDetail() {
  const { id } = useParams();
  const { status, data, error } = useProduct(id);

  if (status === "loading") {
    return (
      <div className="detail-page">
        <LoadingSkeleton />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="detail-page">
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  if (status === "empty" || !data) {
    return (
      <div className="detail-page">
        <p className="muted">No product selected.</p>
      </div>
    );
  }

  const platforms = withMissingPlatforms(data.platforms);

  return (
    <div className="detail-page">
      <ProductHeader
        name={data.canonical_name}
        brand={data.brand}
        imageUrl={data.image_url}
      />

      <Section title="Price Comparison">
        <PriceTable platforms={platforms} />
      </Section>

      <Section title="Availability by Pincode">
        <AvailabilitySection platforms={platforms} />
      </Section>
    </div>
  );
}
