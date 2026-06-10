const PLATFORM_LABELS = {
  blinkit: "Blinkit",
  zepto: "Zepto",
  instamart: "Instamart",
};

function formatTimestamp(raw) {
  if (!raw) return "—";
  try {
    return new Date(raw).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return raw;
  }
}

function AvailabilityRow({ platform, listed, live_pincodes, total_pincodes, oos_pincodes, scraped_at }) {
  const allLive = listed && live_pincodes === total_pincodes && total_pincodes > 0;
  const noneLive = listed && live_pincodes === 0;

  return (
    <div className="availability-row">
      <div className="availability-row-header">
        <span className={`platform-badge platform-badge--${platform}`}>
          {PLATFORM_LABELS[platform] ?? platform}
        </span>
        {listed ? (
          <span
            className={`avail-summary ${allLive ? "avail-all" : noneLive ? "avail-none" : "avail-partial"}`}
          >
            Live in {live_pincodes} of {total_pincodes} pincodes
          </span>
        ) : (
          <span className="avail-summary muted">Not listed on this platform</span>
        )}
      </div>

      {listed && oos_pincodes?.length > 0 && (
        <div className="oos-list">
          <span className="muted oos-label">Out of stock: </span>
          {oos_pincodes.map((pin) => (
            <span key={pin} className="pincode-tag">{pin}</span>
          ))}
        </div>
      )}

      <p className="scraped-at muted">Last scraped {formatTimestamp(scraped_at)}</p>
    </div>
  );
}

export default function AvailabilitySection({ platforms }) {
  if (!platforms?.length) {
    return <p className="muted">No availability data.</p>;
  }

  return (
    <div className="availability-section">
      {platforms.map((p) => (
        <AvailabilityRow key={p.platform} {...p} />
      ))}
    </div>
  );
}
