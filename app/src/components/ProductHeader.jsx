export default function ProductHeader({ name, brand, imageUrl }) {
  return (
    <div className="product-header">
      <div className="product-image-wrap">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="product-image"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              e.currentTarget.nextSibling.style.display = "flex";
            }}
          />
        ) : null}
        <div
          className="product-image-fallback"
          style={{ display: imageUrl ? "none" : "flex" }}
        >
          {brand?.[0] ?? "?"}
        </div>
      </div>
      <div>
        <p className="product-brand">{brand}</p>
        <h1 className="product-name">{name}</h1>
      </div>
    </div>
  );
}
