import { useState } from "react";

const titles = {
  variant: "Add a product variant",
  tax: "Create a tax rule",
  discount: "Create a discount",
  template: "Create a quotation template",
};

export default function CatalogEditor({ type, products, plans, busy, error, onClose, onSave }) {
  const [scope, setScope] = useState("subscription");
  const [kind, setKind] = useState("percent");
  const [lines, setLines] = useState([{ product_id: "", variant_id: "", quantity: 1 }]);

  function updateLine(index, field, value) {
    setLines((current) => current.map((line, position) => position === index
      ? { ...line, [field]: value, ...(field === "product_id" ? { variant_id: "" } : {}) }
      : line));
  }

  function submit(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    if (type === "template") values.lines = lines;
    void onSave(type, values);
  }

  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <form className="payment-modal data-editor catalog-editor" onSubmit={submit}>
      <button className="modal-close" type="button" aria-label="Close" disabled={busy} onClick={onClose}>×</button>
      <span className="modal-icon">✦</span>
      <p className="eyebrow">CATALOG SETUP</p>
      <h2>{titles[type]}</h2>
      <p className="modal-help">Saved to your Brightloop catalog and available for future subscriptions.</p>
      {error && <div className="api-alert editor-alert" role="alert">{error}</div>}

      {type === "variant" && <>
        <label className="form-label" htmlFor="variant-product">Product</label>
        <select id="variant-product" name="product_id" defaultValue="" required><option value="" disabled>Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select>
        <label className="form-label" htmlFor="variant-name">Variant name</label>
        <input className="editor-input" id="variant-name" name="name" required maxLength={200} placeholder="Odoo" />
        <label className="form-label" htmlFor="variant-price">Added price (INR)</label>
        <input className="editor-input" id="variant-price" name="price_delta" type="number" min="0" step="0.01" required placeholder="560.00" />
      </>}

      {type === "tax" && <>
        <label className="form-label" htmlFor="tax-name">Tax name</label>
        <input className="editor-input" id="tax-name" name="name" required maxLength={200} placeholder="GST 18%" />
        <label className="form-label" htmlFor="tax-rate">Rate (%)</label>
        <input className="editor-input" id="tax-rate" name="rate" type="number" min="0" max="100" step="0.01" required placeholder="18" />
      </>}

      {type === "discount" && <>
        <label className="form-label" htmlFor="discount-name">Rule name</label>
        <input className="editor-input" id="discount-name" name="name" required maxLength={200} placeholder="Volume reward" />
        <div className="editor-two-col"><div><label className="form-label" htmlFor="discount-kind">Discount type</label><select id="discount-kind" name="kind" value={kind} onChange={(event) => setKind(event.target.value)}><option value="percent">Percentage</option><option value="fixed">Fixed amount</option></select></div><div><label className="form-label" htmlFor="discount-value">{kind === "percent" ? "Percent (%)" : "Amount (INR)"}</label><input className="editor-input" id="discount-value" name="value" type="number" min="0" max={kind === "percent" ? "100" : undefined} step="0.01" required /></div></div>
        <label className="form-label" htmlFor="discount-scope">Applies to</label>
        <select id="discount-scope" name="scope" value={scope} onChange={(event) => setScope(event.target.value)}><option value="subscription">Whole subscription</option><option value="product">One product</option></select>
        {scope === "product" && <><label className="form-label" htmlFor="discount-product">Product</label><select id="discount-product" name="product_id" defaultValue="" required><option value="" disabled>Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></>}
        <div className="editor-two-col"><div><label className="form-label" htmlFor="discount-min-purchase">Minimum purchase (INR)</label><input className="editor-input" id="discount-min-purchase" name="min_purchase" type="number" min="0" step="0.01" defaultValue="0" /></div><div><label className="form-label" htmlFor="discount-min-quantity">Minimum quantity</label><input className="editor-input" id="discount-min-quantity" name="min_quantity" type="number" min="0" step="1" defaultValue="0" /></div></div>
        <div className="editor-two-col"><div><label className="form-label" htmlFor="discount-start">Starts on</label><input className="editor-input" id="discount-start" name="starts_on" type="date" /></div><div><label className="form-label" htmlFor="discount-end">Ends on</label><input className="editor-input" id="discount-end" name="ends_on" type="date" /></div></div>
        <label className="form-label" htmlFor="discount-limit">Usage limit <span className="field-optional">Optional</span></label><input className="editor-input" id="discount-limit" name="usage_limit" type="number" min="1" step="1" placeholder="Unlimited" />
        {scope === "subscription" && <p className="form-hint">Create the rule here, then assign it to a subscription to apply it.</p>}
      </>}

      {type === "template" && <>
        <label className="form-label" htmlFor="template-name">Template name</label><input className="editor-input" id="template-name" name="name" required maxLength={200} placeholder="Growth + integration" />
        <div className="editor-two-col"><div><label className="form-label" htmlFor="template-plan">Plan</label><select id="template-plan" name="plan_id" defaultValue="" required><option value="" disabled>Select plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select></div><div><label className="form-label" htmlFor="template-valid">Valid for (days)</label><input className="editor-input" id="template-valid" name="valid_days" type="number" min="1" step="1" defaultValue="14" required /></div></div>
        <div className="editor-lines-heading"><strong>Product lines</strong><button type="button" onClick={() => setLines((current) => [...current, { product_id: "", variant_id: "", quantity: 1 }])}>+ Add line</button></div>
        {lines.map((line, index) => {
          const product = products.find((item) => item.id === Number(line.product_id));
          return <div className="editor-line" key={index}>
            <select aria-label={`Product for line ${index + 1}`} value={line.product_id} onChange={(event) => updateLine(index, "product_id", event.target.value)} required><option value="" disabled>Select product</option>{products.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <select aria-label={`Variant for line ${index + 1}`} value={line.variant_id} onChange={(event) => updateLine(index, "variant_id", event.target.value)}><option value="">No variant</option>{(product?.variants || []).map((variant) => <option key={variant.id} value={variant.id}>{variant.name}</option>)}</select>
            <input aria-label={`Quantity for line ${index + 1}`} type="number" min="1" step="1" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} required />
            <button type="button" aria-label={`Remove line ${index + 1}`} disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, position) => position !== index))}>×</button>
          </div>;
        })}
      </>}

      <div className="modal-actions"><button className="button" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={busy || (type === "variant" && !products.length) || (type === "template" && (!plans.length || !products.length))}>{busy ? "Saving…" : "Create"}</button></div>
    </form>
  </div>;
}
