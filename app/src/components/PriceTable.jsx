const PLATFORM_LABELS = {
  blinkit: "Blinkit",
  zepto: "Zepto",
  instamart: "Instamart",
};

function fmt(n) {
  return n != null ? `₹${n}` : "—";
}

export default function PriceTable({ platforms }) {
  if (!platforms?.length) {
    return <p className="muted">No pricing data available.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="price-table">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Selling Price</th>
            <th>MRP</th>
            <th>Discount</th>
          </tr>
        </thead>
        <tbody>
          {platforms.map((p) => (
            <tr key={p.platform} className={!p.listed ? "missing-row" : undefined}>
              <td className="platform-cell">
                <span className={`platform-badge platform-badge--${p.platform}`}>
                  {PLATFORM_LABELS[p.platform] ?? p.platform}
                </span>
              </td>
              <td className="price-cell">{p.listed ? fmt(p.selling_price) : "Not listed"}</td>
              <td className="mrp-cell">{p.listed ? fmt(p.mrp) : "—"}</td>
              <td>
                {p.discount_pct != null ? (
                  <span className="discount-badge">{p.discount_pct}% off</span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
