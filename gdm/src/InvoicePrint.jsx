import { useEffect } from "react";

function money(paise) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format((paise || 0) / 100);
}

function date(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

export default function InvoicePrint({ invoice, onClose }) {
  useEffect(() => {
    document.title = `${invoice.number} · Brightloop invoice`;
    return () => { document.title = "Brightloop"; };
  }, [invoice.number]);

  const lines = invoice.snapshot?.lines || [];
  return (
    <main className="print-page">
      <div className="print-actions">
        <button className="button" onClick={onClose}>Back</button>
        <button className="button button-primary" onClick={() => window.print()}>Print invoice</button>
      </div>
      <article className="invoice-paper">
        <header className="invoice-paper-header">
          <div className="auth-brand"><span className="brand-mark"><span /></span><span>brightloop<span className="brand-dot">.</span></span></div>
          <div className="invoice-wordmark"><span>INVOICE</span><strong>{invoice.number}</strong></div>
        </header>
        <div className="invoice-meta">
          <div><small>BILLED TO</small><strong>{invoice.customer_name}</strong><span>Subscription {invoice.subscription_number || invoice.subscription_id}</span></div>
          <div><small>ISSUED</small><strong>{date(invoice.issued_on)}</strong></div>
          <div><small>DUE DATE</small><strong>{date(invoice.due_on)}</strong></div>
        </div>
        <div className="invoice-period">Billing period: {date(invoice.period_start)} – {date(invoice.period_end)}</div>
        <table className="invoice-lines">
          <thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Tax</th><th className="invoice-amount">Amount</th></tr></thead>
          <tbody>{lines.map((line, index) => (
            <tr key={`${line.description || "line"}-${index}`}>
              <td><strong>{line.description || "Subscription charge"}</strong>{line.discount_paise > 0 && <small>Discount: −{money(line.discount_paise)}</small>}</td>
              <td>{line.quantity ?? 1}</td>
              <td>{money(line.unit_price_paise ?? line.amount_paise)}</td>
              <td>{money(line.tax_paise)}</td>
              <td className="invoice-amount">{money(line.amount_paise ?? line.unit_price_paise)}</td>
            </tr>
          ))}</tbody>
        </table>
        <section className="invoice-totals">
          <div><span>Subtotal</span><strong>{money(invoice.subtotal_paise)}</strong></div>
          <div><span>Discount</span><strong>−{money(invoice.discount_paise)}</strong></div>
          <div><span>Tax</span><strong>{money(invoice.tax_paise)}</strong></div>
          <div className="invoice-grand-total"><span>Total</span><strong>{money(invoice.total_paise)}</strong></div>
          <div><span>Paid</span><strong>{money(invoice.paid_paise)}</strong></div>
          <div className="invoice-balance"><span>Balance due</span><strong>{money(invoice.balance_paise)}</strong></div>
        </section>
        <footer className="invoice-paper-footer">
          <strong>Thank you for your business.</strong>
          <span>This invoice reflects the saved billing snapshot and is issued by Brightloop.</span>
        </footer>
      </article>
    </main>
  );
}
