import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Auth from "./Auth.jsx";
import CatalogEditor from "./CatalogEditor.jsx";
import InvoicePrint from "./InvoicePrint.jsx";
import { apiList, apiRequest, clearToken, getToken, storeToken } from "./api.js";

const navItems = [
  { id: "overview", label: "Overview", icon: "grid" },
  { id: "subscriptions", label: "Subscriptions", icon: "repeat" },
  { id: "quotations", label: "Quotations", icon: "file" },
  { id: "invoices", label: "Invoices", icon: "receipt" },
  { id: "catalog", label: "Products & plans", icon: "box" },
  { id: "customers", label: "Customers", icon: "users" },
];

const iconPaths = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /></>,
  repeat: <><path d="m17 2 4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15" /><path d="m7 22-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" /></>,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
  receipt: <><path d="M4 3v18l3-2 3 2 3-2 3 2 4-2V3l-4 2-3-2-3 2-3-2z" /><path d="M8 9h8M8 13h6" /></>,
  box: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="M3 8v9l9 5 9-5V8M12 13v9" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 11h18" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  alert: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4-.1Z" /><path d="M12 9v4M12 17h.01" /></>,
  download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5M12 15V3" /></>,
  chevron: <path d="m9 18 6-6-6-6" />,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
  spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z" /><path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z" /></>,
};

function Icon({ name, size = 18 }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {iconPaths[name]}
    </svg>
  );
}

function money(paise) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);
}

function dateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function normalizeSubscription(subscription, plans, products, invoices, user) {
  const planId = typeof subscription.plan === "object" ? subscription.plan.id : subscription.plan;
  const plan = plans.find((item) => item.id === planId);
  const customerId = typeof subscription.customer === "object" ? subscription.customer.id : subscription.customer;
  const linkedInvoice = invoices.find((invoice) => invoice.customer_id === customerId);
  const customerName = user.role === "customer"
    ? user.company_name || user.full_name
    : linkedInvoice?.customer_name || (typeof subscription.customer === "object"
      ? subscription.customer.full_name || subscription.customer.email
      : `Customer #${customerId}`);
  const lineValue = (subscription.lines || []).reduce((total, line) =>
    total + (line.unit_price_paise || 0) * (line.quantity || 0), 0);
  const lines = (subscription.lines || []).map((line) => {
    const productId = typeof line.product_id === "object" ? line.product_id.id : line.product_id;
    const variantId = typeof line.variant_id === "object" ? line.variant_id.id : line.variant_id;
    const product = products.find((item) => item.id === productId);
    const variant = product?.variants?.find((item) => item.id === variantId);
    return {
      ...line,
      description: variant ? `${product?.name || "Product"} · ${variant.name}` : product?.name || "Product",
    };
  });

  return {
    ...subscription,
    customer_id: customerId,
    customer: customerName,
    plan_id: planId,
    plan: plan?.name || `Plan #${planId}`,
    frequency: plan?.frequency || "",
    mrr_paise: (plan?.base_price_paise || 0) + lineValue,
    lines,
    permitted_actions: subscription.permitted_actions || [],
  };
}

function normalizeInvoice(invoice, subscriptions) {
  const subscription = subscriptions.find((item) => item.id === invoice.subscription_id);
  return {
    ...invoice,
    subscription: subscription?.number || `Subscription #${invoice.subscription_id}`,
  };
}

function catalogCustomers(invoices, subscriptions, currentUser) {
  const customersById = new Map();
  for (const invoice of invoices) {
    if (invoice.customer_id) {
      customersById.set(invoice.customer_id, {
        id: invoice.customer_id,
        name: invoice.customer_name,
        email: "",
      });
    }
  }
  for (const subscription of subscriptions) {
    if (subscription.customer_id && !customersById.has(subscription.customer_id)) {
      customersById.set(subscription.customer_id, {
        id: subscription.customer_id,
        name: subscription.customer,
        email: "",
      });
    }
  }
  if (currentUser.role === "customer") {
    customersById.set(currentUser.id, {
      id: currentUser.id,
      name: currentUser.company_name || currentUser.full_name,
      email: currentUser.email,
    });
  }
  return [...customersById.values()].map((customer, index) => ({
    ...customer,
    initials: customer.name.split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase(),
    subs: subscriptions.filter((subscription) => subscription.customer_id === customer.id).length,
    color: ["lavender", "mint", "peach"][index % 3],
  }));
}

function shortDate(date) {
  if (!date || date === "—") return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${date}T00:00:00`));
}

function Status({ children, tone }) {
  const statusTone = tone || String(children).toLowerCase().replaceAll(" ", "-");
  return <span className={`status status-${statusTone}`}>{children}</span>;
}

function Button({ children, kind = "secondary", icon, onClick, className = "", type = "button", disabled = false }) {
  return (
    <button className={`button button-${kind} ${className}`} onClick={onClick} type={type} disabled={disabled}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  );
}

function LegacyDemoApp() {
  const [page, setPage] = useState("overview");
  const [customerMode, setCustomerMode] = useState(false);
  const [preview, setPreview] = useState(initialPreview);
  const [invoices, setInvoices] = useState(initialInvoices);
  const [subscriptions, setSubscriptions] = useState(initialSubscriptions);
  const [runResult, setRunResult] = useState(null);
  const [notice, setNotice] = useState("");
  const [paymentInvoice, setPaymentInvoice] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("500");
  const [search, setSearch] = useState("");
  const [quoteCreated, setQuoteCreated] = useState(false);

  const pageTitle = customerMode
    ? "Your subscriptions"
    : navItems.find((item) => item.id === page)?.label || "Overview";
  const visibleInvoices = customerMode
    ? invoices.filter((invoice) => invoice.customer_name === "Example Shop")
    : invoices;
  const visibleSubscriptions = customerMode
    ? subscriptions.filter((subscription) => subscription.customer === "Example Shop")
    : subscriptions;
  const filteredInvoices = useMemo(
    () => visibleInvoices.filter((invoice) =>
      `${invoice.number} ${invoice.customer_name}`.toLowerCase().includes(search.toLowerCase()),
    ),
    [visibleInvoices, search],
  );
  const outstanding = visibleInvoices.reduce((sum, invoice) => sum + invoice.balance_paise, 0);
  const collected = visibleInvoices.reduce((sum, invoice) => sum + invoice.paid_paise, 0);

  function showNotice(message) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3800);
  }

  function runBilling() {
    if (preview.due_count === 0) {
      setRunResult({
        created_count: 0,
        skipped_count: 0,
        error_count: 0,
        invoices: [],
        errors: [],
      });
      showNotice("Billing run complete. No new invoices were due.");
      return;
    }

    const newInvoices = preview.items.map((item, index) => ({
      id: 25 + index,
      number: `INV-${String(25 + index).padStart(4, "0")}`,
      customer_name: item.customer_name,
      subscription: item.number,
      issued_on: preview.as_of,
      due_on: "2026-11-07",
      total_paise: item.total_paise,
      paid_paise: 0,
      balance_paise: item.total_paise,
      status: "confirmed",
      is_overdue: false,
    }));
    setInvoices((current) => [...newInvoices, ...current.filter(
      (invoice) => !newInvoices.some((created) => created.subscription === invoice.subscription),
    )]);
    setRunResult({
      created_count: newInvoices.length,
      skipped_count: 0,
      error_count: 0,
      invoices: newInvoices.map((invoice, index) => ({
        id: invoice.id,
        number: invoice.number,
        subscription_id: preview.items[index].subscription_id,
        total_paise: invoice.total_paise,
      })),
      errors: [],
    });
    setSubscriptions((current) => current.map((subscription) =>
      preview.items.some((item) => item.subscription_id === subscription.id)
        ? { ...subscription, next_bill_date: "2026-11-30" }
        : subscription,
    ));
    setPreview({ ...preview, due_count: 0, expected_total_paise: 0, items: [] });
    showNotice(`${newInvoices.length} invoice${newInvoices.length === 1 ? "" : "s"} created successfully.`);
  }

  function recordPayment(event) {
    event.preventDefault();
    const amountPaise = Math.round(Number(paymentAmount) * 100);
    const invoice = invoices.find((item) => item.id === paymentInvoice);
    if (!invoice || !Number.isFinite(amountPaise) || amountPaise <= 0 || amountPaise > invoice.balance_paise) {
      showNotice("Enter a payment greater than zero and no more than the remaining balance.");
      return;
    }
    setInvoices((current) => current.map((item) => {
      if (item.id !== paymentInvoice) return item;
      const paid = item.paid_paise + amountPaise;
      const balance = item.total_paise - paid;
      return {
        ...item,
        paid_paise: paid,
        balance_paise: balance,
        status: balance === 0 ? "paid" : "confirmed",
      };
    }));
    setPaymentInvoice(null);
    setPaymentAmount("500");
    showNotice(`Payment of ${money(amountPaise)} recorded.`);
  }

  function transitionSubscription(id, action) {
    const labels = { pause: "paused", resume: "resumed", renew: "renewal started", close: "cancelled" };
    const status = { pause: "paused", resume: "active", renew: "active", close: "closed" }[action];
    setSubscriptions((current) => current.map((subscription) =>
      subscription.id === id
        ? {
          ...subscription,
          status,
          permitted_actions: action === "pause"
            ? ["resume", "renew", "close"]
            : action === "resume"
              ? ["pause", "renew", "close"]
              : subscription.permitted_actions,
        }
        : subscription,
    ));
    showNotice(`Subscription ${labels[action]}.`);
  }

  function navigate(id) {
    setCustomerMode(false);
    setPage(id);
    setSearch("");
  }

  return (
    <div className={`app-shell ${customerMode ? "customer-shell" : ""}`}>
      {!customerMode && (
        <aside className="sidebar">
          <a className="brand" href="#" onClick={(event) => { event.preventDefault(); navigate("overview"); }}>
            <span className="brand-mark"><span /></span>
            <span>brightloop<span className="brand-dot">.</span></span>
          </a>
          <div className="workspace-switch">
            <span className="workspace-avatar">B</span>
            <span className="workspace-copy"><strong>Brightloop Inc.</strong><small>Workspace</small></span>
            <span className="workspace-chevron"><Icon name="chevron" size={14} /></span>
          </div>
          <p className="nav-caption">WORKSPACE</p>
          <nav className="side-nav" aria-label="Main navigation">
            {navItems.map((item) => (
              <button
                className={`nav-link ${page === item.id ? "nav-link-active" : ""}`}
                key={item.id}
                aria-label={item.label}
                onClick={() => navigate(item.id)}
              >
                <Icon name={item.icon} size={18} />
                <span>{item.label}</span>
                {item.id === "invoices" && invoices.some((invoice) => invoice.balance_paise > 0) && (
                  <span className="nav-badge">{invoices.filter((invoice) => invoice.balance_paise > 0).length}</span>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-spacer" />
          <div className="help-card">
            <span className="help-icon"><Icon name="spark" size={17} /></span>
            <strong>Need a hand?</strong>
            <p>Your billing team is one click away.</p>
            <button onClick={() => showNotice("Support: hello@brightloop.in")}>Contact support <span>→</span></button>
          </div>
          <button className="nav-link settings-link" onClick={() => showNotice("Workspace settings are coming soon.")}>
            <span className="settings-symbol">⚙</span><span>Settings</span>
          </button>
          <button className="profile-button" onClick={() => setCustomerMode(true)}>
            <span className="profile-avatar">BA</span>
            <span className="profile-copy"><strong>Brightloop Admin</strong><small>Workspace owner</small></span>
            <Icon name="more" size={17} />
          </button>
        </aside>
      )}

      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark"><span /></span> brightloop<span className="brand-dot">.</span>
          </div>
          <div className="breadcrumb">
            {!customerMode && <span>Workspace</span>}
            {!customerMode && <Icon name="chevron" size={13} />}
            <strong>{customerMode ? "Customer portal" : pageTitle}</strong>
          </div>
          <div className="topbar-actions">
            <label className="search-field">
              <Icon name="search" size={17} />
              <input aria-label="Search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search anything..." />
              <kbd>⌘ K</kbd>
            </label>
            <button className="icon-button notification-button" aria-label="Notifications" onClick={() => showNotice("You're all caught up.")}>
              <span className="notification-dot" /><Icon name="bell" size={16} />
            </button>
            <button className="portal-switch" onClick={() => { setCustomerMode(!customerMode); setPage("overview"); setSearch(""); }}>
              {customerMode ? "← Staff view" : "Customer view"}
            </button>
          </div>
        </header>

        <main className="page-content">
          {customerMode ? (
            <CustomerPortal
              subscriptions={visibleSubscriptions}
              invoices={visibleInvoices}
              onAction={transitionSubscription}
              onPay={(id) => { setPaymentInvoice(id); setPaymentAmount("500"); }}
              onInvoice={() => showNotice("Invoice print view is ready for the demo.")}
            />
          ) : page === "overview" ? (
            <Overview
              preview={preview}
              invoices={invoices}
              subscriptions={subscriptions}
              runResult={runResult}
              onRun={runBilling}
              onPayment={(invoice) => { setPaymentInvoice(invoice.id); setPaymentAmount("500"); }}
              onNavigate={navigate}
            />
          ) : page === "subscriptions" ? (
            <Subscriptions subscriptions={subscriptions} onAction={transitionSubscription} onNavigate={navigate} />
          ) : page === "quotations" ? (
            <Quotations created={quoteCreated} onCreate={() => {
              setQuoteCreated(true);
              showNotice("Quotation QUO-0013 created as a draft.");
            }} />
          ) : page === "invoices" ? (
            <Invoices
              invoices={filteredInvoices}
              onPayment={(invoice) => { setPaymentInvoice(invoice.id); setPaymentAmount("500"); }}
              onPrint={() => window.print()}
            />
          ) : page === "catalog" ? (
            <Catalog subscriptions={subscriptions} onCreate={() => showNotice("Catalog editor is ready for API integration.")} />
          ) : (
            <Customers
              invoices={invoices}
              onAdd={() => showNotice("Add a customer with the registration API after identity integration.")}
              onCustomer={() => { setCustomerMode(true); }}
            />
          )}
        </main>
      </div>

      {notice && <div className="toast" role="status"><span className="toast-check"><Icon name="check" size={15} /></span>{notice}</div>}
      {paymentInvoice !== null && (
        <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setPaymentInvoice(null); }}>
          <form className="payment-modal" onSubmit={recordPayment}>
            <button className="modal-close" type="button" aria-label="Close" onClick={() => setPaymentInvoice(null)}>×</button>
            <span className="modal-icon"><Icon name="receipt" size={20} /></span>
            <p className="eyebrow">Record payment</p>
            <h2>{invoices.find((invoice) => invoice.id === paymentInvoice)?.number}</h2>
            <p className="modal-help">Enter a partial or full payment amount. This demo records the payment locally.</p>
            <label className="form-label" htmlFor="payment-amount">Amount (INR)</label>
            <div className="amount-input"><span>₹</span><input id="payment-amount" type="number" min="0.01" step="0.01" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} autoFocus required /></div>
            <label className="form-label" htmlFor="payment-method">Payment method</label>
            <select id="payment-method" defaultValue="bank"><option value="bank">Bank transfer</option><option value="card">Card</option><option value="cash">Cash</option><option value="upi">UPI</option></select>
            <div className="modal-actions"><Button onClick={() => setPaymentInvoice(null)}>Cancel</Button><Button kind="primary" type="submit">Record payment</Button></div>
          </form>
        </div>
      )}
    </div>
  );
}

function Overview({ preview: loadedPreview, dashboard, invoices, subscriptions, runResult, onRun, onPayment, onNavigate, loading }) {
  const preview = loadedPreview || {
    as_of: dateInputValue(new Date()),
    due_count: 0,
    expected_total_paise: 0,
    items: [],
    exceptions: [],
  };
  const paid = dashboard?.collected_paise ?? 0;
  const outstanding = dashboard?.outstanding_paise ?? 0;
  const overdue = dashboard?.overdue_count ?? 0;
  const monthInvoiced = dashboard?.invoiced_paise ?? 0;
  const activeSubscriptions = subscriptions.filter((subscription) => subscription.status === "active");
  const activeCount = dashboard?.active_count ?? activeSubscriptions.length;
  const grossMrr = dashboard?.gross_mrr_paise ?? 0;

  return (
    <div className="overview-page">
      <div className="overview-hero">
        <div className="hero-orbit" aria-hidden="true" />
        <div className="welcome-strip">
          <div><span className="welcome-sun">✳</span> {shortDate(preview.as_of)} <span className="strip-divider">·</span> Revenue operations</div>
          <span className="demo-label"><span /> LIVE WORKSPACE</span>
        </div>
        <div className="hero-body">
          <div className="hero-copy">
            <p className="hero-kicker"><span /> YOUR REVENUE, IN FOCUS</p>
            <h1>Billing control <em>tower.</em></h1>
            <p className="hero-description">See every renewal before it runs. Turn complex billing into a clear, confident next step.</p>
            <div className="hero-actions">
              <Button kind="primary" icon="repeat" onClick={onRun} disabled={loading}>{loading ? "Loading…" : "Run billing"}</Button>
              <button className="hero-text-action" onClick={() => document.getElementById("preview-table")?.scrollIntoView({ behavior: "smooth", block: "center" })}>Explore this cycle <Icon name="chevron" size={16} /></button>
            </div>
          </div>
          <div className="hero-insight" aria-label="Current billing cycle summary">
            <div className="hero-insight-top"><span className="hero-live-dot" /> READY FOR THIS CYCLE <Icon name="spark" size={18} /></div>
            <strong>{money(preview.expected_total_paise)}</strong>
            <p>Expected from {preview.due_count} subscription{preview.due_count === 1 ? "" : "s"} due</p>
            <div className="hero-insight-divider" />
            <div className="hero-insight-bottom"><span>Billing status</span><b>{preview.exceptions.length ? `${preview.exceptions.length} need attention` : "All checks clear"}</b></div>
          </div>
        </div>
      </div>

      <section className="metric-grid" aria-label="Business metrics">
        <Metric label="Active subscriptions" value={activeCount} detail="Billing right now" icon="repeat" tone="blue" />
        <Metric label="Gross monthly recurring" value={money(grossMrr)} detail="Before tax & discounts" icon="arrow" tone="purple" />
        <Metric label="Collected" value={money(paid)} detail="Recorded payments" icon="check" tone="green" />
        <Metric label="Outstanding balance" value={money(outstanding)} detail={`${overdue} overdue invoice${overdue === 1 ? "" : "s"}`} icon="clock" tone="amber" />
      </section>

      <section className="tower-panel">
        <div className="tower-header">
          <div className="tower-title">
            <span className="tower-icon"><Icon name="spark" size={19} /></span>
            <div><p className="eyebrow">THE BILLING ENGINE</p><h2>Upcoming billing run</h2><p>Preview recurring invoices before they go out.</p></div>
          </div>
          <span className="date-chip"><Icon name="calendar" size={15} /> As of {shortDate(preview.as_of)} <span className="date-caret">⌄</span></span>
        </div>
        <div className="tower-summary">
          <div><span>SUBSCRIPTIONS DUE</span><strong>{preview.due_count}</strong><small>ready for billing</small></div>
          <div><span>EXPECTED TOTAL</span><strong>{money(preview.expected_total_paise)}</strong><small>including taxes</small></div>
          <div><span>NEEDS ATTENTION</span><strong className={preview.exceptions.length ? "attention-value" : ""}>{preview.exceptions.length}</strong><small>{preview.exceptions.length ? "exceptions to resolve" : "all clear"}</small></div>
          <Button kind="dark" icon="arrow" onClick={() => document.getElementById("preview-table")?.scrollIntoView({ behavior: "smooth", block: "center" })}>Review preview</Button>
        </div>
        <div className="table-section" id="preview-table">
          <div className="table-heading"><div><h3>Invoice preview</h3><span>{preview.due_count ? "Review the calculated totals before running billing." : "No subscriptions are due for this run."}</span></div><button className="subtle-link" onClick={() => onNavigate("subscriptions")}>View subscriptions <Icon name="chevron" size={14} /></button></div>
          <PreviewTable items={preview.items} />
          {preview.exceptions.length > 0 && <div className="exception-row"><Icon name="alert" size={16} /> {preview.exceptions.length} subscription(s) need attention before billing.</div>}
        </div>
        {runResult && <div className="run-result">
          <div className="run-check"><Icon name="check" size={17} /></div>
          <div className="run-copy"><strong>{runResult.created_count ? "Billing run complete" : "Run complete — nothing new to bill"}</strong><span>{runResult.created_count} invoice{runResult.created_count === 1 ? "" : "s"} created · {runResult.skipped_count} skipped · {runResult.error_count} errors</span></div>
          {runResult.invoices.length > 0 && <button className="subtle-link" onClick={() => onNavigate("invoices")}>View invoices <Icon name="chevron" size={14} /></button>}
        </div>}
        <div className="tower-footer"><span><span className="lock-symbol">✓</span> Preview and billing use the same pricing rules.</span><button onClick={() => onNavigate("invoices")}>Billing history <Icon name="chevron" size={13} /></button></div>
      </section>

      <section className="lower-grid">
        <div className="content-card revenue-card">
          <div className="card-heading"><div><p className="eyebrow">REVENUE</p><h2>Collection health</h2></div><span className="select-chip">Current demo ledger</span></div>
          <div className="revenue-totals"><div><span>Invoiced</span><strong>{money(monthInvoiced)}</strong></div><span className="revenue-divider" /><div><span>Collected</span><strong>{money(paid)}</strong></div></div>
          <RevenueChart invoiced={monthInvoiced} collected={paid} />
        </div>
        <div className="content-card attention-card">
          <div className="card-heading"><div><p className="eyebrow">FOLLOW UP</p><h2>Needs attention <span className="count-bubble">{overdue}</span></h2></div><button className="more-button" aria-label="More options"><Icon name="more" /></button></div>
          {invoices.filter((invoice) => invoice.is_overdue && invoice.balance_paise > 0).length > 0 ? (
            invoices.filter((invoice) => invoice.is_overdue && invoice.balance_paise > 0).slice(0, 3).map((invoice) => (
              <div className="attention-item" key={invoice.id}>
                <span className="customer-avatar mint">{invoice.customer_name.slice(0, 1)}</span>
                <div className="attention-copy"><strong>{invoice.customer_name}</strong><small>{invoice.number} · Overdue</small></div>
                <div className="attention-amount"><strong>{money(invoice.balance_paise)}</strong><button onClick={() => onPayment(invoice)}>Record payment</button></div>
              </div>
            ))
          ) : (
            <div className="empty-attention"><span className="empty-check"><Icon name="check" /></span><strong>All caught up</strong><small>No overdue invoices need attention.</small></div>
          )}
          <button className="attention-footer" onClick={() => onNavigate("invoices")}>See all invoices <Icon name="chevron" size={14} /></button>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, detail, icon, tone }) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span>{label}</span><span className={`metric-icon metric-icon-${tone}`}><Icon name={icon} size={16} /></span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail"><span className={`metric-detail-dot metric-detail-${tone}`} />{detail}</div>
    </article>
  );
}

function PreviewTable({ items }) {
  if (items.length === 0) {
    return <div className="table-empty"><span className="empty-check"><Icon name="check" /></span><div><strong>All clear for now</strong><small>When a subscription is due, it’ll appear here before billing.</small></div></div>;
  }
  return (
    <div className="table-scroll">
      <table className="data-table preview-table">
        <thead><tr><th>SUBSCRIPTION</th><th>CUSTOMER</th><th>BILLING PERIOD</th><th>SUBTOTAL</th><th>DISCOUNT</th><th>TAX</th><th className="align-right">TOTAL</th><th /></tr></thead>
        <tbody>{items.map((item) => (
          <tr key={item.subscription_id}>
            <td><strong className="table-primary">{item.number}</strong><small className="table-secondary">Subscription</small></td>
            <td><span className="table-customer"><span className="customer-avatar lavender">{item.customer_name.slice(0, 1)}</span>{item.customer_name}</span></td>
            <td><strong className="table-primary">{shortDate(item.period_start)} –</strong><small className="table-secondary">{shortDate(item.period_end)}</small></td>
            <td>{money(item.subtotal_paise)}</td>
            <td>{item.discount_paise ? `−${money(item.discount_paise)}` : "—"}</td>
            <td>{money(item.tax_paise)}</td>
            <td className="align-right"><strong>{money(item.total_paise)}</strong></td>
            <td><button className="row-more" aria-label={`More options for ${item.number}`}><Icon name="more" size={16} /></button></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function RevenueChart({ invoiced, collected }) {
  const percent = invoiced > 0 ? Math.min(100, Math.round((collected / invoiced) * 100)) : 0;
  return (
    <div className="collection-progress" aria-label={`${percent}% of invoiced amount collected`}>
      <div className="collection-ring" style={{ "--collection-percent": `${percent}%` }}><div><strong>{percent}%</strong><span>collected</span></div></div>
      <div className="collection-breakdown">
        <p>Every rupee, accounted for.</p>
        <div><span><i className="legend-dot collected-dot" />Collected</span><strong>{money(collected)}</strong></div>
        <div><span><i className="legend-dot remaining-dot" />To collect</span><strong>{money(Math.max(0, invoiced - collected))}</strong></div>
        <small>Based on invoices shown in this demo workspace.</small>
      </div>
    </div>
  );
}

function Subscriptions({ subscriptions, onAction, onNavigate }) {
  return (
    <>
      <PageHeader eyebrow="CUSTOMER LIFECYCLE" title="Subscriptions" subtitle="Manage plans, renewals, and customer access." action={<Button kind="primary" icon="plus" onClick={() => onNavigate("quotations")}>New subscription</Button>} />
      <div className="metric-grid compact-metrics">
        <SimpleMetric label="Active" value={subscriptions.filter((item) => item.status === "active").length} helper="Generating recurring revenue" icon="repeat" />
        <SimpleMetric label="Monthly recurring revenue" value={money(subscriptions.filter((item) => item.status === "active").reduce((sum, item) => sum + item.mrr_paise, 0))} helper="From active subscriptions" icon="arrow" />
        <SimpleMetric label="Paused" value={subscriptions.filter((item) => item.status === "paused").length} helper="Can resume at any time" icon="clock" />
      </div>
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>All subscriptions</h2><span>{subscriptions.length} records</span></div><Button icon="file" onClick={() => window.print()}>Print</Button></div>
        <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>SUBSCRIPTION</th><th>CUSTOMER</th><th>PLAN</th><th>STATUS</th><th>NEXT BILLING</th><th>MONTHLY VALUE</th><th /></tr></thead>
          <tbody>{subscriptions.map((subscription) => <tr key={subscription.id}>
            <td><strong className="table-primary">{subscription.number}</strong><small className="table-secondary">Started {shortDate(subscription.start_date)}</small></td>
            <td>{subscription.customer}</td><td>{subscription.plan}</td>
            <td><Status>{subscription.status}</Status></td><td>{shortDate(subscription.next_bill_date)}</td>
            <td><strong>{money(subscription.mrr_paise)}</strong></td>
            <td><select className="row-action-select" aria-label={`Actions for ${subscription.number}`} value="" onChange={(event) => { if (event.target.value) onAction(subscription.id, event.target.value); }}>
              <option value="">Actions</option>{subscription.permitted_actions.map((action) => <option value={action} key={action}>{action[0].toUpperCase() + action.slice(1)}</option>)}
            </select></td>
          </tr>)}</tbody>
        </table></div>
      </section>
    </>
  );
}

function Quotations({ subscriptions, customers, plans, products, onCreate }) {
  const quotations = subscriptions.filter((subscription) =>
    ["draft", "quotation"].includes(subscription.status),
  );
  return (
    <>
      <PageHeader eyebrow="SALES WORKFLOW" title="Quotations" subtitle="Turn a customer’s needs into a subscription, one step at a time." action={<Button kind="primary" icon="plus" onClick={onCreate}>Create quotation</Button>} />
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>Quotes & drafts</h2><span>{quotations.length} records</span></div><span className="select-chip">Subscription status <span>⌄</span></span></div>
        {quotations.length ? <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>QUOTE</th><th>CUSTOMER</th><th>PLAN</th><th>CREATED</th><th>VALID UNTIL</th><th>STATUS</th><th /></tr></thead>
          <tbody>{quotations.map((subscription) => {
            const customer = customers.find((item) => item.id === subscription.customer_id);
            const plan = plans.find((item) => item.id === subscription.plan_id);
            return <tr key={subscription.id}>
              <td><strong className="table-primary">{subscription.number}</strong><small className="table-secondary">Subscription quote</small></td>
              <td>{customer?.name || subscription.customer}</td><td>{plan?.name || subscription.plan}</td>
              <td>{shortDate(subscription.start_date)}</td><td>{subscription.quote_expires_at ? shortDate(subscription.quote_expires_at.slice(0, 10)) : "—"}</td>
              <td><Status>{subscription.status}</Status></td><td>{products.length === 0 ? null : <span className="table-secondary">{subscription.lines?.length || 0} line items</span>}</td>
            </tr>;
          })}</tbody>
        </table></div> : <div className="table-empty"><span className="empty-check"><Icon name="file" /></span><div><strong>No open quotations</strong><small>Create a quotation to start a customer subscription.</small></div></div>}
      </section>
      <div className="journey-note"><span className="modal-icon"><Icon name="spark" size={18} /></span><div><strong>From quote to recurring revenue</strong><p>When a customer accepts a quotation, activate their subscription and they’ll automatically appear in your next billing preview.</p></div></div>
    </>
  );
}

function Invoices({ invoices, onConfirm, onPayment, onPrint, onInvoice }) {
  return (
    <>
      <PageHeader eyebrow="BILLING & PAYMENTS" title="Invoices" subtitle="Every invoice, payment, and outstanding balance in one place." action={<Button icon="file" onClick={onPrint}>Print</Button>} />
      <section className="metric-grid compact-metrics invoice-metrics">
        <SimpleMetric label="Invoiced" value={money(invoices.reduce((sum, item) => sum + item.total_paise, 0))} helper="Across listed invoices" icon="receipt" />
        <SimpleMetric label="Collected" value={money(invoices.reduce((sum, item) => sum + item.paid_paise, 0))} helper="Payments received" icon="check" />
        <SimpleMetric label="Outstanding" value={money(invoices.reduce((sum, item) => sum + item.balance_paise, 0))} helper="Remaining balances" icon="clock" />
      </section>
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>All invoices</h2><span>{invoices.length} records</span></div><span className="select-chip">All statuses <span>⌄</span></span></div>
        {invoices.length ? <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>INVOICE</th><th>CUSTOMER</th><th>ISSUED</th><th>DUE DATE</th><th>AMOUNT</th><th>STATUS</th><th /></tr></thead>
          <tbody>{invoices.map((invoice) => <tr key={invoice.id}>
            <td><button className="invoice-number-link" onClick={() => onInvoice(invoice)}>{invoice.number}</button><small className="table-secondary">{invoice.subscription}</small></td>
            <td>{invoice.customer_name}</td><td>{shortDate(invoice.issued_on)}</td><td>{shortDate(invoice.due_on)}</td>
            <td><strong>{money(invoice.total_paise)}</strong><small className="table-secondary">{invoice.balance_paise > 0 ? `${money(invoice.balance_paise)} due` : "Paid in full"}</small></td>
            <td><Status tone={invoice.balance_paise === 0 ? "paid" : invoice.is_overdue ? "overdue" : "confirmed"}>{invoice.balance_paise === 0 ? "Paid" : invoice.is_overdue ? "Overdue" : invoice.paid_paise ? "Partial" : invoice.status}</Status></td>
            <td><button className="table-action-link" onClick={() => onInvoice(invoice)}>View / print</button>{invoice.status === "draft" && <button className="table-action-link" onClick={() => onConfirm(invoice)}>Confirm</button>}{invoice.status === "confirmed" && invoice.balance_paise > 0 && <button className="table-action-link" onClick={() => onPayment(invoice)}>Record payment</button>}</td>
          </tr>)}</tbody>
        </table></div> : <div className="table-empty"><span className="empty-check"><Icon name="search" /></span><div><strong>No invoices found</strong><small>Try adjusting your search.</small></div></div>}
      </section>
    </>
  );
}

function Catalog({ products, plans, taxes, discounts, templates, subscriptions, canManage, onCreateProduct, onCreatePlan, onCreateExtra }) {
  const variantCount = products.reduce((total, product) => total + (product.variants?.length || 0), 0);
  return (
    <>
      <PageHeader eyebrow="YOUR OFFERING" title="Products & plans" subtitle="Keep your catalog tidy and your subscription plans clear." action={canManage && <Button kind="primary" icon="plus" onClick={onCreateProduct}>Add product</Button>} />
      <section className="catalog-spotlight" aria-label="Catalog summary">
        <div className="catalog-spotlight-copy"><p className="catalog-spotlight-kicker"><span /> THE OFFERING</p><h2>Built to grow with every customer.</h2><p>One view of the products, variations, and recurring plans behind your subscriptions.</p></div>
        <div className="catalog-spotlight-stats">
          <div><strong>{products.length}</strong><span>Product{products.length === 1 ? "" : "s"}</span></div>
          <div><strong>{variantCount}</strong><span>Variant{variantCount === 1 ? "" : "s"}</span></div>
          <div><strong>{plans.length}</strong><span>Recurring plan{plans.length === 1 ? "" : "s"}</span></div>
        </div>
      </section>
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>Products & add-ons</h2><span>Services and one-time items customers can add</span></div><span className="select-chip">{products.length} products</span></div>
        {products.length ? <div className={`catalog-grid ${products.length === 1 ? "catalog-grid-single" : ""}`}>{products.map((product, index) => <article className="catalog-item" key={product.id}>
          <div className="catalog-item-header"><span className={`product-icon ${["lavender", "mint", "peach"][index % 3]}`}><Icon name="box" size={20} /></span><Status tone={product.active ? "active" : "expired"}>{product.active ? "Active" : "Inactive"}</Status></div>
          <div className="catalog-main"><h3>{product.name}</h3><p>{product.notes || (product.variants?.length ? "Available with your choice of variant." : "Ready to add to a subscription.")}</p></div>
          {product.variants?.length > 0 && <div className="catalog-variant-list">{product.variants.map((variant) => <span key={variant.id}>{variant.name}<strong>+{money(variant.price_delta_paise)}</strong></span>)}</div>}
          <div className="catalog-item-footer"><span>{product.type}{canManage && <button className="catalog-inline-action" onClick={() => onCreateExtra("variant")}>+ Add variant</button>}</span><div><small>Base price</small><strong>{money(product.sale_price_paise)}</strong></div></div>
        </article>)}</div> : <div className="table-empty"><span className="empty-check"><Icon name="box" /></span><div><strong>No products yet</strong><small>Add a product to build your catalog.</small></div></div>}
      </section>
      <section className="content-card list-card plans-card">
        <div className="list-toolbar"><div><h2>Subscription plans</h2><span>Recurring pricing your customers can count on</span></div>{canManage && <Button onClick={onCreatePlan} icon="plus">Add plan</Button>}</div>
        {plans.length ? <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>PLAN</th><th>BILLING</th><th>BASE PRICE</th><th>SUBSCRIBERS</th><th>STATUS</th><th /></tr></thead>
          <tbody>{plans.map((plan) => <tr key={plan.id}><td><strong className="table-primary">{plan.name}</strong></td><td>Billed {plan.frequency}</td><td><strong>{money(plan.base_price_paise)}</strong></td><td>{subscriptions.filter((subscription) => subscription.plan_id === plan.id).length}</td><td><Status tone="active">Available</Status></td><td /></tr>)}</tbody>
        </table></div> : <div className="table-empty"><span className="empty-check"><Icon name="repeat" /></span><div><strong>No plans yet</strong><small>Create a plan to start a quotation.</small></div></div>}
      </section>
      <section className="catalog-rules-grid" aria-label="Catalog rules and templates">
        <div className="content-card catalog-rule-card"><div className="catalog-rule-heading"><div><p className="eyebrow">PRICING</p><h2>Taxes</h2></div>{canManage && <button onClick={() => onCreateExtra("tax")}>+ Add tax</button>}</div><div className="catalog-rule-list">{taxes.length ? taxes.map((tax) => <div key={tax.id}><span><strong>{tax.name}</strong><small>{tax.active ? "Active" : "Inactive"}</small></span><b>{(tax.rate_bps / 100).toFixed(2).replace(/\.00$/, "")}%</b></div>) : <p>No tax rules yet.</p>}</div></div>
        <div className="content-card catalog-rule-card"><div className="catalog-rule-heading"><div><p className="eyebrow">INCENTIVES</p><h2>Discounts</h2></div>{canManage && <button onClick={() => onCreateExtra("discount")}>+ Add rule</button>}</div><div className="catalog-rule-list">{discounts.length ? discounts.map((discount) => <div key={discount.id}><span><strong>{discount.name}</strong><small>{discount.scope === "product" ? "Product rule" : "Subscription rule"} · {discount.used_count}{discount.usage_limit ? ` / ${discount.usage_limit}` : ""} used</small></span><b>{discount.kind === "percent" ? `${(discount.value / 100).toFixed(2).replace(/\.00$/, "")}%` : money(discount.value)}</b></div>) : <p>No discounts yet.</p>}</div></div>
        <div className="content-card catalog-rule-card"><div className="catalog-rule-heading"><div><p className="eyebrow">SALES</p><h2>Quote templates</h2></div>{canManage && <button onClick={() => onCreateExtra("template")}>+ Add template</button>}</div><div className="catalog-rule-list">{templates.length ? templates.map((template) => <div key={template.id}><span><strong>{template.name}</strong><small>{template.lines?.length || 0} line{template.lines?.length === 1 ? "" : "s"}</small></span><b>{template.valid_days} days</b></div>) : <p>No quotation templates yet.</p>}</div></div>
      </section>
    </>
  );
}

function Customers({ customers, invoices, canAdd, onAdd, onCustomer }) {
  return (
    <>
      <PageHeader eyebrow="PEOPLE & RELATIONSHIPS" title="Customers" subtitle="Customers with billing activity and accounts added in this session." action={canAdd && <Button kind="primary" icon="plus" onClick={onAdd}>Add customer</Button>} />
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>Customers</h2><span>{customers.length} customer accounts available</span></div></div>
        <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>CUSTOMER</th><th>SUBSCRIPTIONS</th><th>OPEN BALANCE</th><th>STATUS</th><th /></tr></thead>
          <tbody>{customers.map((customer) => <tr key={customer.id}>
            <td><span className="customer-cell"><span className={`customer-avatar ${customer.color}`}>{customer.initials}</span><span><strong className="table-primary">{customer.name}</strong><small className="table-secondary">{customer.email || `Customer account #${customer.id}`}</small></span></span></td>
            <td>{customer.subs} subscription{customer.subs === 1 ? "" : "s"}</td><td><strong>{money(invoices.filter((invoice) => invoice.customer_id === customer.id).reduce((sum, invoice) => sum + invoice.balance_paise, 0))}</strong></td><td><Status tone="active">Known</Status></td><td />
          </tr>)}</tbody>
        </table></div>
      </section>
      <div className="portal-promo"><div><span className="modal-icon"><Icon name="users" /></span><span><strong>Give customers a place of their own</strong><small>Switch to the customer view to see subscriptions and invoices from their perspective.</small></span></div><Button kind="primary" onClick={onCustomer}>Preview customer portal</Button></div>
    </>
  );
}

function CustomerPortal({ user, subscriptions, invoices, onAction, onInvoice }) {
  const activeSubscription = subscriptions[0];
  const displayName = user.company_name || user.full_name;
  return (
    <>
      <div className="portal-welcome"><div className="portal-avatar">{displayName.slice(0, 1).toUpperCase()}</div><div><p className="eyebrow">WELCOME BACK</p><h1>Hello, {displayName}</h1><p>Here’s your subscription at a glance.</p></div><span className="portal-tag"><span /> CUSTOMER PORTAL</span></div>
      {activeSubscription ? <>
        <section className="portal-subscription">
          <div className="portal-sub-header"><div><span className="eyebrow">YOUR SUBSCRIPTION</span><Status tone={activeSubscription.status}>{activeSubscription.status}</Status></div><button className="row-more" aria-label="Subscription options"><Icon name="more" /></button></div>
          <h2>{activeSubscription.plan}</h2><p className="portal-sub-number">{activeSubscription.number} · Started {shortDate(activeSubscription.start_date)}</p>
          <div className="portal-sub-stats"><div><small>Subscription price</small><strong>{money(activeSubscription.mrr_paise)}</strong></div><div><small>Next billing date</small><strong>{shortDate(activeSubscription.next_bill_date)}</strong></div><div><small>Plan</small><strong>{activeSubscription.plan}</strong><small>{activeSubscription.frequency || "Recurring subscription"}</small></div></div>
          {activeSubscription.permitted_actions.length > 0 && <div className="portal-actions">{activeSubscription.permitted_actions.map((action) => <Button key={action} onClick={() => onAction(activeSubscription.id, action)}>{action === "close" ? "Cancel subscription" : action[0].toUpperCase() + action.slice(1)}</Button>)}</div>}
        </section>
        <section className="content-card list-card portal-invoices">
          <div className="list-toolbar"><div><h2>Your invoices</h2><span>Access your invoice history</span></div></div>
          {invoices.length ? <div className="table-scroll"><table className="data-table full-table">
            <thead><tr><th>INVOICE</th><th>ISSUED</th><th>AMOUNT</th><th>STATUS</th><th /></tr></thead>
            <tbody>{invoices.map((invoice) => <tr key={invoice.id}><td><button className="invoice-number-link" onClick={() => onInvoice(invoice)}>{invoice.number}</button><small className="table-secondary">Due {shortDate(invoice.due_on)}</small></td><td>{shortDate(invoice.issued_on)}</td><td><strong>{money(invoice.total_paise)}</strong><small className="table-secondary">{invoice.balance_paise > 0 ? `${money(invoice.balance_paise)} remaining` : "Paid in full"}</small></td><td><Status tone={invoice.balance_paise === 0 ? "paid" : invoice.paid_paise ? "partial" : invoice.status}>{invoice.balance_paise === 0 ? "Paid" : invoice.paid_paise ? "Partial" : "Due"}</Status></td><td><button className="table-action-link" onClick={() => onInvoice(invoice)}>View invoice</button></td></tr>)}</tbody>
          </table></div> : <div className="table-empty portal-empty"><span className="empty-check"><Icon name="receipt" /></span><div><strong>No invoices yet</strong><small>Your invoices will appear here after your next billing run.</small></div></div>}
        </section>
      </> : <div className="table-empty"><span className="empty-check"><Icon name="repeat" /></span><div><strong>No active subscriptions</strong><small>There are no subscriptions available for this account.</small></div></div>}
      <footer className="portal-footer">Secure customer portal <span>·</span> Need help? <a href="mailto:hello@brightloop.in">Contact Brightloop</a></footer>
    </>
  );
}

function PageHeader({ eyebrow, title, subtitle, action }) {
  return <section className="page-heading heading-with-action"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="heading-subtitle">{subtitle}</p></div>{action}</section>;
}

function SimpleMetric({ label, value, helper, icon }) {
  return <article className="simple-metric"><span className="metric-icon metric-icon-blue"><Icon name={icon} size={16} /></span><span className="simple-metric-label">{label}</span><strong>{value}</strong><small>{helper}</small></article>;
}

function DataEditor({ type, busy, error, customers, plans, products, taxes, discounts, templates, onClose, onCreateProduct, onCreatePlan, onCreateQuotation, onRegisterCustomer }) {
  const [selectedProductId, setSelectedProductId] = useState(String(products.find((product) => product.active)?.id || ""));
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [submitError, setSubmitError] = useState("");
  const activeProducts = products.filter((product) => product.active);
  const selectedProduct = activeProducts.find((product) => product.id === Number(selectedProductId));
  const variants = selectedProduct?.variants || [];
  const titles = {
    product: "Add product",
    plan: "Create a subscription plan",
    quotation: "Create a quotation",
    customer: "Add customer account",
  };
  const callbacks = {
    product: onCreateProduct,
    plan: onCreatePlan,
    quotation: onCreateQuotation,
    customer: onRegisterCustomer,
  };
  const canCreateQuotation = customers.length > 0 && (templates.length > 0 || (plans.length > 0 && activeProducts.length > 0));

  function submit(event) {
    event.preventDefault();
    setSubmitError("");
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    Promise.resolve(callbacks[type](values)).catch((requestError) => setSubmitError(requestError.message));
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <form className="payment-modal data-editor" onSubmit={submit}>
        <button className="modal-close" type="button" aria-label="Close" disabled={busy} onClick={onClose}>×</button>
        <span className="modal-icon"><Icon name={type === "customer" ? "users" : type === "quotation" ? "file" : "box"} size={20} /></span>
        <p className="eyebrow">BRIGHTLOOP WORKSPACE</p>
        <h2>{titles[type]}</h2>
        <p className="modal-help">The information is saved through the authenticated Brightloop API.</p>
        {(submitError || error) && <div className="api-alert editor-alert" role="alert">{submitError || error}</div>}

        {type === "product" && <>
          <label className="form-label" htmlFor="product-name">Product name</label>
          <input className="editor-input" id="product-name" name="name" required maxLength={200} />
          <label className="form-label" htmlFor="product-type">Type</label>
          <input className="editor-input" id="product-type" name="type" placeholder="service" required maxLength={80} />
          <label className="form-label" htmlFor="product-sale-price">Sale price (INR)</label>
          <input className="editor-input" id="product-sale-price" name="sale_price" type="number" min="0" step="0.01" required />
          <label className="form-label" htmlFor="product-cost-price">Internal cost (INR)</label>
          <input className="editor-input" id="product-cost-price" name="cost_price" type="number" min="0" step="0.01" defaultValue="0" />
          <label className="form-label" htmlFor="product-notes">Notes</label>
          <textarea className="editor-input" id="product-notes" name="notes" rows="2" maxLength={2000} />
          <label className="form-label" htmlFor="product-tax">Tax</label><select id="product-tax" name="tax_id" defaultValue=""><option value="">No tax</option>{taxes.filter((tax) => tax.active).map((tax) => <option key={tax.id} value={tax.id}>{tax.name} · {tax.rate_bps / 100}%</option>)}</select>
        </>}

        {type === "plan" && <>
          <label className="form-label" htmlFor="plan-name">Plan name</label>
          <input className="editor-input" id="plan-name" name="name" required maxLength={200} />
          <label className="form-label" htmlFor="plan-frequency">Billing frequency</label>
          <select id="plan-frequency" name="frequency" defaultValue="monthly" required><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select>
          <label className="form-label" htmlFor="plan-price">Base price (INR)</label>
          <input className="editor-input" id="plan-price" name="base_price" type="number" min="0" step="0.01" required />
          <label className="form-label" htmlFor="plan-minimum">Minimum quantity</label>
          <input className="editor-input" id="plan-minimum" name="minimum_quantity" type="number" min="1" step="1" defaultValue="1" required />
          <label className="form-label" htmlFor="plan-tax">Tax</label><select id="plan-tax" name="tax_id" defaultValue=""><option value="">No tax</option>{taxes.filter((tax) => tax.active).map((tax) => <option key={tax.id} value={tax.id}>{tax.name} · {tax.rate_bps / 100}%</option>)}</select>
          <div className="editor-two-col"><div><label className="form-label" htmlFor="plan-from">Available from</label><input className="editor-input" id="plan-from" name="available_from" type="date" /></div><div><label className="form-label" htmlFor="plan-to">Available to</label><input className="editor-input" id="plan-to" name="available_to" type="date" /></div></div>
          <fieldset className="editor-checks"><legend>Plan controls</legend><label><input type="checkbox" name="auto_close" /> Auto-close at expiry</label><label><input type="checkbox" name="allow_pause" defaultChecked /> Allow pause</label><label><input type="checkbox" name="allow_renew" defaultChecked /> Allow renewal</label><label><input type="checkbox" name="allow_cancel" defaultChecked /> Allow early close</label></fieldset>
        </>}

        {type === "customer" && <>
          <label className="form-label" htmlFor="customer-name">Full name</label>
          <input className="editor-input" id="customer-name" name="full_name" required maxLength={200} />
          <label className="form-label" htmlFor="customer-company">Company</label>
          <input className="editor-input" id="customer-company" name="company_name" maxLength={200} />
          <label className="form-label" htmlFor="customer-email">Email address</label>
          <input className="editor-input" id="customer-email" name="email" type="email" required maxLength={254} />
          <label className="form-label" htmlFor="customer-password">Temporary password</label>
          <input className="editor-input" id="customer-password" name="password" type="password" autoComplete="new-password" minLength="10" required />
        </>}

        {type === "quotation" && <>
          <label className="form-label" htmlFor="quote-customer">Customer</label>
          <select id="quote-customer" name="customer" defaultValue="" required><option value="" disabled>Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name} · #{customer.id}</option>)}</select>
          {templates.length > 0 && <><label className="form-label" htmlFor="quote-template">Start from template</label><select id="quote-template" name="template_id" value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}><option value="">Build a custom quotation</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.name} · valid {template.valid_days} days</option>)}</select></>}
          {!selectedTemplateId && <>
            <label className="form-label" htmlFor="quote-plan">Plan</label>
            <select id="quote-plan" name="plan" defaultValue="" required><option value="" disabled>Select plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {money(plan.base_price_paise)} / {plan.frequency}</option>)}</select>
            <label className="form-label" htmlFor="quote-product">Product</label>
            <select id="quote-product" name="product" value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)} required><option value="" disabled>Select product</option>{activeProducts.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select>
            {variants.length > 0 && <><label className="form-label" htmlFor="quote-variant">Variant</label><select id="quote-variant" name="variant" defaultValue=""><option value="">No variant</option>{variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.name} · {money(variant.price_delta_paise)} surcharge</option>)}</select></>}
            <label className="form-label" htmlFor="quote-quantity">Quantity</label>
            <input className="editor-input" id="quote-quantity" name="quantity" type="number" min="1" step="1" defaultValue="1" required />
          </>}
          {discounts.some((discount) => discount.scope === "subscription" && discount.active) && <><label className="form-label" htmlFor="quote-discount">Subscription discount</label><select id="quote-discount" name="subscription_discount_id" defaultValue=""><option value="">No discount</option>{discounts.filter((discount) => discount.scope === "subscription" && discount.active).map((discount) => <option key={discount.id} value={discount.id}>{discount.name}</option>)}</select></>}
          <label className="form-label" htmlFor="quote-start">Start date</label>
          <input className="editor-input" id="quote-start" name="start_date" type="date" defaultValue={dateInputValue(new Date())} required />
          <label className="form-label" htmlFor="quote-expiry">Expiry date (exclusive)</label>
          <input className="editor-input" id="quote-expiry" name="expiry_date" type="date" min={dateInputValue(new Date(Date.now() + 86400000))} defaultValue={dateInputValue(new Date(Date.now() + 365 * 86400000))} required />
          {!canCreateQuotation && <div className="form-hint">Add a customer and either a template or a plan with an active product before creating a quotation.</div>}
        </>}

        <div className="modal-actions"><Button onClick={onClose}>Cancel</Button><Button kind="primary" type="submit" disabled={busy || (type === "quotation" && !canCreateQuotation)}>{busy ? "Saving…" : "Save"}</Button></div>
      </form>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("overview");
  const [user, setUser] = useState(null);
  const [authRestoring, setAuthRestoring] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [dataLoading, setDataLoading] = useState(false);
  const [dataErrors, setDataErrors] = useState({});
  const [operationError, setOperationError] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [preview, setPreview] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [products, setProducts] = useState([]);
  const [plans, setPlans] = useState([]);
  const [taxes, setTaxes] = useState([]);
  const [discounts, setDiscounts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [customerAccounts, setCustomerAccounts] = useState([]);
  const [runResult, setRunResult] = useState(null);
  const [notice, setNotice] = useState("");
  const [paymentInvoice, setPaymentInvoice] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("bank");
  const [actionBusy, setActionBusy] = useState(false);
  const [editor, setEditor] = useState("");
  const [printInvoice, setPrintInvoice] = useState(null);
  const [search, setSearch] = useState("");
  const dataRequestId = useRef(0);
  const customerMode = user?.role === "customer";
  const pageTitle = customerMode ? "Your subscriptions" : navItems.find((item) => item.id === page)?.label || "Overview";
  const customers = useMemo(
    () => user
      ? [...new Map([
        ...catalogCustomers(invoices, subscriptions, user),
        ...customerAccounts,
      ].map((customer) => [customer.id, customer])).values()]
      : [],
    [customerAccounts, invoices, subscriptions, user],
  );
  const filteredInvoices = useMemo(
    () => invoices.filter((invoice) =>
      `${invoice.number} ${invoice.customer_name}`.toLowerCase().includes(search.toLowerCase()),
    ),
    [invoices, search],
  );

  const loadData = useCallback(async () => {
    if (!user) return;
    const requestId = ++dataRequestId.current;
    setDataLoading(true);
    setDataErrors({});
    const now = new Date();
    const from = dateInputValue(new Date(now.getFullYear(), now.getMonth(), 1));
    const to = dateInputValue(now);
    const requests = [
      apiList("/api/subscriptions"),
      apiList("/api/invoices"),
      ...(customerMode ? [] : [
        apiList("/api/products"),
        apiList("/api/plans"),
        apiRequest(`/api/dashboard?from=${from}&to=${to}`),
        apiRequest("/api/billing/preview"),
        apiList("/api/taxes"),
        apiList("/api/discounts"),
        apiList("/api/templates"),
      ]),
    ];
    const results = await Promise.allSettled(requests);
    if (requestId !== dataRequestId.current) return;
    const subscriptionResult = results[0];
    const invoiceResult = results[1];
    const subscriptionData = subscriptionResult.status === "fulfilled" ? subscriptionResult.value : [];
    const invoiceData = invoiceResult.status === "fulfilled" ? invoiceResult.value : [];
    const productsResult = customerMode ? null : results[2];
    const plansResult = customerMode ? null : results[3];
    const dashboardResult = customerMode ? null : results[4];
    const previewResult = customerMode ? null : results[5];
    const taxesResult = customerMode ? null : results[6];
    const discountsResult = customerMode ? null : results[7];
    const templatesResult = customerMode ? null : results[8];
    const productsData = productsResult?.status === "fulfilled" ? productsResult.value : [];
    const plansData = plansResult?.status === "fulfilled" ? plansResult.value : [];
    const normalizedSubs = subscriptionData.map((item) => normalizeSubscription(item, plansData, productsData, invoiceData, user));
    setSubscriptions(normalizedSubs);
    setInvoices(invoiceData.map((item) => normalizeInvoice(item, normalizedSubs)));
    if (customerMode) {
      setProducts([]);
      setPlans([]);
      setTaxes([]);
      setDiscounts([]);
      setTemplates([]);
      setDashboard(null);
      setPreview(null);
    } else {
      setProducts(productsData);
      setPlans(plansData);
      setTaxes(taxesResult?.status === "fulfilled" ? taxesResult.value : []);
      setDiscounts(discountsResult?.status === "fulfilled" ? discountsResult.value : []);
      setTemplates(templatesResult?.status === "fulfilled" ? templatesResult.value : []);
      setDashboard(dashboardResult?.status === "fulfilled" ? dashboardResult.value : null);
      setPreview(previewResult?.status === "fulfilled" ? previewResult.value : null);
    }

    const labels = ["subscriptions", "invoices", ...(customerMode ? [] : ["products", "plans", "dashboard", "billing preview", "taxes", "discounts", "templates"])];
    const failures = {};
    results.forEach((result, index) => {
      if (result.status === "rejected") failures[labels[index]] = result.reason.message;
    });
    setDataErrors(failures);
    setDataLoading(false);
  }, [customerMode, user]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthRestoring(false);
      return;
    }
    let active = true;
    apiRequest("/api/auth/me", { token })
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch((error) => {
        if (error.status === 401 || error.status === 403) clearToken();
        if (active) setAuthError(error.message);
      })
      .finally(() => { if (active) setAuthRestoring(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (user && !authRestoring) void loadData();
  }, [authRestoring, loadData, user]);

  async function submitAuth(mode, values) {
    setAuthBusy(true);
    setAuthError("");
    try {
      if (mode === "register") {
        await apiRequest("/api/auth/register", {
          method: "POST",
          token: null,
          body: {
            email: values.email,
            password: values.password,
            full_name: values.full_name,
            company_name: values.company_name || "",
          },
        });
      }
      const result = await apiRequest("/api/auth/login", {
        method: "POST",
        token: null,
        body: { email: values.email, password: values.password },
      });
      storeToken(result.token);
      setUser(result.user);
      setPage("overview");
      setOperationError("");
      setDataErrors({});
    } finally {
      setAuthBusy(false);
    }
  }

  function showNotice(message) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3800);
  }

  async function perform(action, message, refresh = true) {
    setOperationError("");
    setActionBusy(true);
    try {
      const result = await action();
      if (refresh) await loadData();
      showNotice(message(result));
      return result;
    } catch (error) {
      setOperationError(error.message);
      return null;
    } finally {
      setActionBusy(false);
    }
  }

  async function runBilling() {
    const result = await perform(
      () => apiRequest("/api/billing/run", { method: "POST", body: {} }),
      (response) => `${response.created_count} invoice${response.created_count === 1 ? "" : "s"} created · ${response.skipped_count} skipped · ${response.error_count} errors.`,
    );
    if (result) setRunResult(result);
  }

  async function recordPayment(event) {
    event.preventDefault();
    const invoice = invoices.find((item) => item.id === paymentInvoice);
    const amountPaise = Math.round(Number(paymentAmount) * 100);
    if (!invoice || !Number.isFinite(amountPaise) || amountPaise <= 0) {
      setOperationError("Enter a payment amount greater than zero.");
      return;
    }
    const result = await perform(
      () => apiRequest(`/api/invoices/${invoice.id}/payments`, {
        method: "POST",
        body: { method: paymentMethod, amount_paise: amountPaise, paid_on: dateInputValue(new Date()), note: "" },
      }),
      () => `Payment of ${money(amountPaise)} recorded.`,
    );
    if (result) setPaymentInvoice(null);
  }

  async function confirmInvoice(invoice) {
    await perform(
      () => apiRequest(`/api/invoices/${invoice.id}/confirm`, { method: "POST", body: {} }),
      () => `${invoice.number} confirmed and ready for payment.`,
    );
  }

  async function transitionSubscription(id, action) {
    const result = await perform(
      () => apiRequest(`/api/subscriptions/${id}/transition`, { method: "POST", body: { action } }),
      (subscription) => `${subscription.number} is now ${subscription.status}.`,
    );
    if (result) setPage("subscriptions");
  }

  async function createCatalogRecord(type, values) {
    const isProduct = type === "product";
    const payload = isProduct ? {
      name: values.name,
      type: values.type,
      sale_price_paise: Math.round(Number(values.sale_price) * 100),
      cost_price_paise: Math.round(Number(values.cost_price || 0) * 100),
      notes: values.notes || "",
      tax_id: values.tax_id ? Number(values.tax_id) : null,
      active: true,
    } : {
      name: values.name,
      frequency: values.frequency,
      base_price_paise: Math.round(Number(values.base_price) * 100),
      minimum_quantity: Number(values.minimum_quantity || 1),
      tax_id: values.tax_id ? Number(values.tax_id) : null,
      available_from: values.available_from || null,
      available_to: values.available_to || null,
      auto_close: values.auto_close === "on",
      allow_pause: values.allow_pause === "on",
      allow_renew: values.allow_renew === "on",
      allow_cancel: values.allow_cancel === "on",
    };
    const result = await perform(
      () => apiRequest(`/api/${isProduct ? "products" : "plans"}`, { method: "POST", body: payload }),
      (record) => `${isProduct ? "Product" : "Plan"} "${record.name}" created.`,
    );
    if (result) setEditor("");
  }

  async function createCatalogExtra(type, values) {
    const paise = (value) => Math.round(Number(value || 0) * 100);
    const payloads = {
      variant: () => ({ name: values.name, price_delta_paise: paise(values.price_delta) }),
      tax: () => ({ name: values.name, rate_bps: paise(values.rate), active: true }),
      discount: () => ({
        name: values.name, kind: values.kind, scope: values.scope,
        value: paise(values.value),
        product_id: values.scope === "product" ? Number(values.product_id) : null,
        min_purchase_paise: paise(values.min_purchase),
        min_quantity: Number(values.min_quantity || 0),
        starts_on: values.starts_on || null, ends_on: values.ends_on || null,
        usage_limit: values.usage_limit ? Number(values.usage_limit) : null,
        active: true,
      }),
      template: () => ({
        name: values.name, plan_id: Number(values.plan_id), valid_days: Number(values.valid_days),
        lines: values.lines.map((line) => ({
          product_id: Number(line.product_id),
          variant_id: line.variant_id ? Number(line.variant_id) : null,
          quantity: Number(line.quantity),
        })),
      }),
    };
    const route = type === "variant" ? `/api/products/${Number(values.product_id)}/variants` : `/api/${type === "tax" ? "taxes" : type === "discount" ? "discounts" : "templates"}`;
    const result = await perform(
      () => apiRequest(route, { method: "POST", body: payloads[type]() }),
      (record) => `${type[0].toUpperCase() + type.slice(1)} "${record.name}" created.`,
    );
    if (result) setEditor("");
  }

  async function createQuotation(values) {
    const result = await perform(async () => {
      const source = values.template_id ? { template_id: Number(values.template_id) } : {
        plan: Number(values.plan),
        lines: [{ product_id: Number(values.product), variant_id: values.variant ? Number(values.variant) : null, quantity: Number(values.quantity || 1) }],
      };
      const subscription = await apiRequest("/api/subscriptions", {
        method: "POST",
        body: {
          customer: Number(values.customer),
          ...source,
          start_date: values.start_date,
          expiry_date: values.expiry_date,
          subscription_discount_id: values.subscription_discount_id ? Number(values.subscription_discount_id) : null,
        },
      });
      return apiRequest(`/api/subscriptions/${subscription.id}/transition`, {
        method: "POST",
        body: { action: "quote" },
      });
    }, (subscription) => `Quotation ${subscription.number} created.`);
    if (result) setEditor("");
  }

  async function registerCustomer(values) {
    const result = await perform(
      () => apiRequest("/api/auth/register", {
        method: "POST",
        body: {
          email: values.email,
          password: values.password,
          full_name: values.full_name,
          company_name: values.company_name,
          role: "customer",
        },
      }),
      (customer) => `Customer account for ${customer.full_name} created.`,
      false,
    );
    if (result) {
      const name = result.company_name || result.full_name;
      setCustomerAccounts((accounts) => [
        ...accounts.filter((account) => account.id !== result.id),
        {
          id: result.id,
          name,
          email: result.email,
          initials: name.split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase(),
          subs: 0,
          color: "lavender",
        },
      ]);
      setEditor("");
    }
  }

  function navigate(id) {
    setPage(id);
    setSearch("");
  }

  function signOut() {
    dataRequestId.current += 1;
    clearToken();
    setUser(null);
    setPage("overview");
    setInvoices([]);
    setSubscriptions([]);
    setProducts([]);
    setPlans([]);
    setTaxes([]);
    setDiscounts([]);
    setTemplates([]);
    setCustomerAccounts([]);
    setPreview(null);
    setDashboard(null);
    setDataErrors({});
    setDataLoading(false);
    setOperationError("");
    setAuthError("");
    setPrintInvoice(null);
  }

  if (authRestoring) return <main className="auth-page"><div className="auth-loading" role="status">Restoring your secure session…</div></main>;
  if (!user) return <Auth onLogin={submitAuth} busy={authBusy} error={authError} />;
  if (printInvoice) return <InvoicePrint invoice={printInvoice} onClose={() => setPrintInvoice(null)} />;

  const visibleNavItems = customerMode ? [] : navItems.filter((item) => item.id !== "customers" || user.role === "admin");
  const canManageCatalog = user.role === "admin";

  return (
    <div className={`app-shell ${customerMode ? "customer-shell" : ""}`}>
      {!customerMode && <aside className="sidebar">
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); navigate("overview"); }}>
          <span className="brand-mark"><span /></span><span>brightloop<span className="brand-dot">.</span></span>
        </a>
        <div className="workspace-switch"><span className="workspace-avatar">{(user.company_name || user.full_name || "B").slice(0, 1)}</span><span className="workspace-copy"><strong>{user.company_name || "Brightloop"}</strong><small>Workspace</small></span></div>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="side-nav" aria-label="Main navigation">
          {visibleNavItems.map((item) => <button className={`nav-link ${page === item.id ? "nav-link-active" : ""}`} key={item.id} aria-label={item.label} onClick={() => navigate(item.id)}>
            <Icon name={item.icon} size={18} /><span>{item.label}</span>
            {item.id === "invoices" && invoices.some((invoice) => invoice.balance_paise > 0) && <span className="nav-badge">{invoices.filter((invoice) => invoice.balance_paise > 0).length}</span>}
          </button>)}
        </nav>
        <div className="sidebar-spacer" />
        <div className="help-card"><span className="help-icon"><Icon name="spark" size={17} /></span><strong>Need a hand?</strong><p>Your billing team is one click away.</p><a href="mailto:hello@brightloop.in">Contact support →</a></div>
        <button className="profile-button" onClick={signOut}><span className="profile-avatar">{user.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")}</span><span className="profile-copy"><strong>{user.full_name}</strong><small>{user.role}</small></span><span className="signout-label">Sign out</span></button>
      </aside>}
      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark"><span /></span> brightloop<span className="brand-dot">.</span></div>
          <div className="breadcrumb">{!customerMode && <><span>Workspace</span><Icon name="chevron" size={13} /></>}<strong>{customerMode ? "Customer portal" : pageTitle}</strong></div>
          <div className="topbar-actions">
            {!customerMode && <label className="search-field"><Icon name="search" size={17} /><input aria-label="Search invoices" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search invoices..." /><kbd>⌘ K</kbd></label>}
            <span className="user-role-chip">{customerMode ? "Customer portal" : user.role === "admin" ? "Administrator" : "Staff workspace"}</span>
            <button className="topbar-signout" onClick={signOut}>Sign out</button>
          </div>
        </header>
        <main className="page-content">
          {Object.keys(dataErrors).length > 0 && <div className="api-alert" role="alert"><strong>Some data could not be loaded</strong><span>{Object.entries(dataErrors).map(([name, error]) => `${name}: ${error}`).join(" · ")}</span><button className="api-retry" onClick={() => void loadData()}>Retry</button></div>}
          {operationError && <div className="api-alert" role="alert"><strong>Action could not be completed</strong><span>{operationError}</span><button className="api-retry" onClick={() => setOperationError("")}>Dismiss</button></div>}
          {dataLoading && <div className="loading-banner" role="status">Loading the latest data from Brightloop…</div>}
          {customerMode ? <CustomerPortal user={user} subscriptions={subscriptions} invoices={invoices} onAction={transitionSubscription} onInvoice={setPrintInvoice} /> :
            page === "overview" ? <Overview preview={preview} dashboard={dashboard} invoices={invoices} subscriptions={subscriptions} runResult={runResult} onRun={runBilling} onPayment={(invoice) => { setPaymentInvoice(invoice.id); setPaymentAmount(""); }} onNavigate={navigate} loading={dataLoading} /> :
            page === "subscriptions" ? <Subscriptions subscriptions={subscriptions} onAction={transitionSubscription} onNavigate={navigate} /> :
            page === "quotations" ? <Quotations subscriptions={subscriptions} customers={customers} plans={plans} products={products} onCreate={() => setEditor("quotation")} /> :
            page === "invoices" ? <Invoices invoices={filteredInvoices} onConfirm={confirmInvoice} onPayment={(invoice) => { setPaymentInvoice(invoice.id); setPaymentAmount(""); }} onPrint={() => filteredInvoices[0] && setPrintInvoice(filteredInvoices[0])} onInvoice={setPrintInvoice} /> :
            page === "catalog" ? <Catalog products={products} plans={plans} taxes={taxes} discounts={discounts} templates={templates} subscriptions={subscriptions} canManage={canManageCatalog} onCreateProduct={() => setEditor("product")} onCreatePlan={() => setEditor("plan")} onCreateExtra={(type) => { setOperationError(""); setEditor(type); }} /> :
            user.role === "admin" ? <Customers customers={customers} invoices={invoices} canAdd onAdd={() => setEditor("customer")} onCustomer={() => showNotice("Choose a customer record to review their billing data.")} /> :
            <Subscriptions subscriptions={subscriptions} onAction={transitionSubscription} onNavigate={navigate} />}
        </main>
      </div>
      {notice && <div className="toast" role="status"><span className="toast-check"><Icon name="check" size={15} /></span>{notice}</div>}
      {paymentInvoice !== null && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setPaymentInvoice(null); }}>
        <form className="payment-modal" onSubmit={recordPayment}>
          <button className="modal-close" type="button" aria-label="Close" onClick={() => setPaymentInvoice(null)}>×</button>
          <span className="modal-icon"><Icon name="receipt" size={20} /></span><p className="eyebrow">Record payment</p>
          <h2>{invoices.find((invoice) => invoice.id === paymentInvoice)?.number}</h2><p className="modal-help">The backend checks this payment against the invoice’s remaining balance.</p>
          <label className="form-label" htmlFor="payment-amount">Amount (INR)</label><div className="amount-input"><span>₹</span><input id="payment-amount" type="number" min="0.01" step="0.01" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} autoFocus required /></div>
          <label className="form-label" htmlFor="payment-method">Payment method</label><select id="payment-method" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="bank">Bank transfer</option><option value="card">Card</option><option value="cash">Cash</option><option value="upi">UPI</option></select>
          <div className="modal-actions"><Button onClick={() => setPaymentInvoice(null)}>Cancel</Button><Button kind="primary" type="submit" disabled={actionBusy}>{actionBusy ? "Recording…" : "Record payment"}</Button></div>
        </form>
      </div>}
      {editor && (["variant", "tax", "discount", "template"].includes(editor)
        ? <CatalogEditor type={editor} products={products} plans={plans} busy={actionBusy} error={operationError} onClose={() => { setEditor(""); setOperationError(""); }} onSave={createCatalogExtra} />
        : <DataEditor type={editor} busy={actionBusy} error={operationError} customers={customers} plans={plans} products={products} taxes={taxes} discounts={discounts} templates={templates} onClose={() => { setEditor(""); setOperationError(""); }} onCreateProduct={(values) => createCatalogRecord("product", values)} onCreatePlan={(values) => createCatalogRecord("plan", values)} onCreateQuotation={createQuotation} onRegisterCustomer={registerCustomer} />)}
    </div>
  );
}

export default App;
