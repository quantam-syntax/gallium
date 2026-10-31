import { useMemo, useState } from "react";

function lineValues(subscription) {
  return (subscription.lines || [])
    .filter((line) => line.active !== false)
    .map((line) => ({
      product_id: String(typeof line.product_id === "object" ? line.product_id.id : line.product_id),
      variant_id: line.variant_id == null ? "" : String(typeof line.variant_id === "object" ? line.variant_id.id : line.variant_id),
      quantity: String(line.quantity),
    }));
}

export default function CustomerAddonEditor({ subscription, products, optionsLoading, busy, error, onClose, onSave }) {
  const [lines, setLines] = useState(() => lineValues(subscription));
  const activeProducts = useMemo(() => products.filter((product) => product.active !== false), [products]);

  function updateLine(index, key, value) {
    setLines((current) => current.map((line, lineIndex) => lineIndex === index
      ? { ...line, [key]: value, ...(key === "product_id" ? { variant_id: "" } : {}) }
      : line));
  }

  function submit(event) {
    event.preventDefault();
    const combined = new Map();
    for (const line of lines) {
      const productId = Number(line.product_id);
      const variantId = line.variant_id ? Number(line.variant_id) : null;
      const key = `${productId}:${variantId ?? ""}`;
      const current = combined.get(key);
      combined.set(key, {
        product_id: productId,
        variant_id: variantId,
        quantity: Number(line.quantity) + (current?.quantity || 0),
      });
    }
    onSave([...combined.values()]);
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <form className="payment-modal addon-editor" onSubmit={submit}>
        <button className="modal-close" type="button" aria-label="Close" disabled={busy} onClick={onClose}>×</button>
        <span className="modal-icon">＋</span>
        <p className="eyebrow">CUSTOMER SUBSCRIPTION</p>
        <h2>Manage products & quantities</h2>
        <p className="modal-help">Changes apply to future invoices without proration. Any billing due through today will use your current items first.</p>
        <div className="addon-subscription-name">{subscription.number} · {subscription.plan}</div>
        {error && <div className="api-alert editor-alert" role="alert">{error}</div>}
        {optionsLoading && <div className="loading-banner" role="status">Loading available products…</div>}
        <div className="addon-lines">
          {lines.map((line, index) => {
            const product = activeProducts.find((item) => item.id === Number(line.product_id));
            const variants = product?.variants || [];
            return <div className="addon-line" key={`${subscription.id}-${index}`}>
              <div className="addon-line-product">
                <label className="form-label" htmlFor={`addon-product-${index}`}>Product</label>
                <select id={`addon-product-${index}`} value={line.product_id} onChange={(event) => updateLine(index, "product_id", event.target.value)} required disabled={optionsLoading || busy}>
                  {activeProducts.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.type}</option>)}
                </select>
              </div>
              <div className="addon-line-variant">
                <label className="form-label" htmlFor={`addon-variant-${index}`}>Variant</label>
                <select id={`addon-variant-${index}`} value={line.variant_id} onChange={(event) => updateLine(index, "variant_id", event.target.value)} disabled={optionsLoading || busy}>
                  <option value="">No variant</option>
                  {variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.name} (+₹{(variant.price_delta_paise / 100).toFixed(2)})</option>)}
                </select>
              </div>
              <div className="addon-line-quantity">
                <label className="form-label" htmlFor={`addon-quantity-${index}`}>Qty</label>
                <input className="editor-input" id={`addon-quantity-${index}`} type="number" min="1" step="1" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} required disabled={optionsLoading || busy} />
              </div>
              <button className="addon-remove" type="button" aria-label={`Remove ${product?.name || "product"}`} disabled={lines.length <= 1 || busy} onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}>Remove</button>
            </div>;
          })}
        </div>
        <button className="addon-add" type="button" disabled={!activeProducts.length || busy || optionsLoading} onClick={() => setLines((current) => [...current, {
          product_id: String(activeProducts[0]?.id || ""),
          variant_id: "",
          quantity: "1",
        }])}>+ Add product</button>
        {!activeProducts.length && <div className="form-hint">There are no active products available to add.</div>}
        <div className="modal-actions"><button className="button" type="button" onClick={onClose} disabled={busy}>Cancel</button><button className="button button-primary" type="submit" disabled={busy || optionsLoading || lines.length === 0 || lines.some((line) => !line.product_id || Number(line.quantity) < 1)}>{busy ? "Saving…" : "Save changes"}</button></div>
      </form>
    </div>
  );
}
