import { useMemo, useState } from "react";

const initialPreview = {
  as_of: "2026-10-31",
  due_count: 1,
  expected_total_paise: 184080,
  items: [
    {
      subscription_id: 12,
      number: "SUB-0012",
      customer_name: "Example Shop",
      period_start: "2026-10-31",
      period_end: "2026-11-30",
      subtotal_paise: 156000,
      discount_paise: 0,
      tax_paise: 28080,
      total_paise: 184080,
      issues: [],
    },
  ],
  exceptions: [],
};

const initialInvoices = [
  {
    id: 24,
    number: "INV-0024",
    customer_name: "Northstar Studio",
    subscription: "SUB-0008",
    issued_on: "2026-10-21",
    due_on: "2026-10-28",
    total_paise: 106200,
    paid_paise: 50000,
    balance_paise: 56200,
    status: "confirmed",
    is_overdue: true,
  },
  {
    id: 23,
    number: "INV-0023",
    customer_name: "Copper & Co",
    subscription: "SUB-0004",
    issued_on: "2026-10-01",
    due_on: "2026-10-08",
    total_paise: 51330,
    paid_paise: 51330,
    balance_paise: 0,
    status: "paid",
    is_overdue: false,
  },
];

const initialSubscriptions = [
  {
    id: 12,
    number: "SUB-0012",
    customer: "Example Shop",
    plan: "Growth monthly",
    status: "active",
    start_date: "2026-10-01",
    next_bill_date: "2026-10-31",
    mrr_paise: 156000,
    permitted_actions: ["pause", "renew", "close"],
    items: "Growth plan + Odoo variant",
  },
  {
    id: 8,
    number: "SUB-0008",
    customer: "Northstar Studio",
    plan: "Scale monthly",
    status: "active",
    start_date: "2026-08-21",
    next_bill_date: "2026-11-21",
    mrr_paise: 90000,
    permitted_actions: ["pause", "renew", "close"],
    items: "Scale plan",
  },
  {
    id: 4,
    number: "SUB-0004",
    customer: "Copper & Co",
    plan: "Starter monthly",
    status: "paused",
    start_date: "2026-06-01",
    next_bill_date: "—",
    mrr_paise: 48500,
    permitted_actions: ["resume", "renew", "close"],
    items: "Starter plan",
  },
];

const customers = [
  { name: "Example Shop", initials: "ES", email: "hello@exampleshop.in", subs: 1, color: "lavender" },
  { name: "Northstar Studio", initials: "NS", email: "finance@northstar.studio", subs: 1, color: "mint" },
  { name: "Copper & Co", initials: "CC", email: "accounts@copper.co", subs: 1, color: "peach" },
];

const productRows = [
  { name: "Odoo integration", type: "Service", detail: "Variant · standard setup", price: 56000, state: "Active", icon: "◈", color: "lavender" },
  { name: "Priority support", type: "Service", detail: "Monthly add-on", price: 25000, state: "Active", icon: "✳", color: "mint" },
  { name: "Onboarding session", type: "One-time", detail: "Remote · 90 minutes", price: 120000, state: "Active", icon: "↗", color: "peach" },
];

const planRows = [
  { name: "Growth monthly", cadence: "Billed monthly", price: 100000, subscribers: 12, state: "Available" },
  { name: "Scale monthly", cadence: "Billed monthly", price: 90000, subscribers: 8, state: "Available" },
  { name: "Starter monthly", cadence: "Billed monthly", price: 48500, subscribers: 26, state: "Available" },
];

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

function Button({ children, kind = "secondary", icon, onClick, className = "", type = "button" }) {
  return (
    <button className={`button button-${kind} ${className}`} onClick={onClick} type={type}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  );
}

function App() {
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
            <span className="profile-avatar">AK</span>
            <span className="profile-copy"><strong>Akash Kishor</strong><small>Admin</small></span>
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
            <Catalog onCreate={() => showNotice("Catalog editor is ready for API integration.")} />
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

function Overview({ preview, invoices, runResult, onRun, onPayment, onNavigate }) {
  const paid = invoices.reduce((sum, invoice) => sum + invoice.paid_paise, 0);
  const outstanding = invoices.reduce((sum, invoice) => sum + invoice.balance_paise, 0);
  const overdue = invoices.filter((invoice) => invoice.is_overdue && invoice.balance_paise > 0).length;
  const monthInvoiced = invoices.reduce((sum, invoice) => sum + invoice.total_paise, 0);

  return (
    <>
      <div className="welcome-strip">
        <div><span className="welcome-sun">✳</span> Saturday, October 31, 2026 <span className="strip-divider">·</span> Good morning, Akash</div>
        <span className="demo-label"><span /> DEMO WORKSPACE</span>
      </div>
      <section className="page-heading heading-with-action">
        <div><p className="eyebrow">YOUR BUSINESS AT A GLANCE</p><h1>Billing control tower</h1><p className="heading-subtitle">A clear view of what’s due, what’s paid, and what needs your attention.</p></div>
        <Button kind="primary" icon="repeat" onClick={onRun}>Run billing</Button>
      </section>

      <section className="metric-grid" aria-label="Business metrics">
        <Metric label="Active subscriptions" value="46" delta="+4.3%" helper="vs. last month" icon="repeat" tone="blue" trend={[27, 38, 31, 46, 39, 57, 48, 69, 61, 77]} />
        <Metric label="Monthly recurring revenue" value={money(8245000)} delta="+8.2%" helper="vs. last month" icon="arrow" tone="purple" trend={[25, 34, 30, 44, 49, 42, 64, 59, 76, 82]} />
        <Metric label="Collected this month" value={money(paid || 6480000)} delta="+12.6%" helper="vs. last month" icon="check" tone="green" trend={[29, 34, 42, 36, 54, 49, 64, 59, 72, 81]} />
        <Metric label="Outstanding balance" value={money(outstanding)} delta={`${overdue} overdue`} helper="needs attention" icon="clock" tone="amber" trend={[57, 48, 55, 39, 48, 32, 38, 28, 35, 25]} />
      </section>

      <section className="tower-panel">
        <div className="tower-header">
          <div className="tower-title">
            <span className="tower-icon"><Icon name="spark" size={19} /></span>
            <div><p className="eyebrow">THE BILLING ENGINE</p><h2>Upcoming billing run</h2><p>Preview recurring invoices before they go out.</p></div>
          </div>
          <span className="date-chip"><Icon name="calendar" size={15} /> As of Oct 31, 2026 <span className="date-caret">⌄</span></span>
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
          <div className="card-heading"><div><p className="eyebrow">REVENUE</p><h2>Cash flow</h2></div><button className="select-chip">Last 30 days <span>⌄</span></button></div>
          <div className="revenue-totals"><div><span>Invoiced</span><strong>{money(monthInvoiced)}</strong></div><span className="revenue-divider" /><div><span>Collected</span><strong>{money(paid || 6480000)}</strong></div><div className="chart-legend"><span /><small>Revenue collected</small></div></div>
          <RevenueChart />
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
    </>
  );
}

function Metric({ label, value, delta, helper, icon, tone, trend }) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span>{label}</span><span className={`metric-icon metric-icon-${tone}`}><Icon name={icon} size={16} /></span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-bottom"><span className={`metric-delta ${tone === "amber" ? "delta-amber" : ""}`}>{delta}</span><span>{helper}</span><MiniTrend data={trend} tone={tone} /></div>
    </article>
  );
}

function MiniTrend({ data, tone }) {
  return <svg className={`mini-trend trend-${tone}`} viewBox="0 0 90 28" aria-hidden="true" preserveAspectRatio="none">
    <polyline points={data.map((point, index) => `${index * 10},${26 - point * 0.25}`).join(" ")} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
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

function RevenueChart() {
  return (
    <div className="chart-wrap" aria-label="Revenue collected trend for the last 30 days">
      <div className="chart-y-labels"><span>₹ 8L</span><span>₹ 6L</span><span>₹ 4L</span><span>₹ 2L</span><span>₹ 0</span></div>
      <svg viewBox="0 0 600 145" preserveAspectRatio="none" className="revenue-chart" role="img" aria-label="Revenue trend rises throughout October">
        <defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#5E73D8" stopOpacity=".22" /><stop offset="100%" stopColor="#5E73D8" stopOpacity="0" /></linearGradient></defs>
        <path d="M0 118 C25 112 32 92 59 99 S100 103 120 79 S157 89 179 82 S216 69 238 76 S274 56 298 63 S335 66 358 48 S397 62 418 44 S453 39 478 43 S511 21 538 31 S572 10 600 15 V145 H0Z" fill="url(#chartFill)" />
        <path d="M0 118 C25 112 32 92 59 99 S100 103 120 79 S157 89 179 82 S216 69 238 76 S274 56 298 63 S335 66 358 48 S397 62 418 44 S453 39 478 43 S511 21 538 31 S572 10 600 15" fill="none" stroke="#6678D8" strokeWidth="2.4" vectorEffect="non-scaling-stroke" />
        {[20, 52, 84, 116].map((y) => <line key={y} x1="0" x2="600" y1={y} y2={y} stroke="#EDF0F6" strokeDasharray="4 5" vectorEffect="non-scaling-stroke" />)}
      </svg>
      <div className="chart-x-labels"><span>Oct 1</span><span>Oct 8</span><span>Oct 15</span><span>Oct 22</span><span>Oct 31</span></div>
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

function Quotations({ created, onCreate }) {
  return (
    <>
      <PageHeader eyebrow="SALES WORKFLOW" title="Quotations" subtitle="Turn a customer’s needs into a subscription, one step at a time." action={<Button kind="primary" icon="plus" onClick={onCreate}>Create quotation</Button>} />
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>Recent quotations</h2><span>{created ? 4 : 3} records</span></div><span className="select-chip">All statuses <span>⌄</span></span></div>
        <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>QUOTE</th><th>CUSTOMER</th><th>PLAN</th><th>CREATED</th><th>VALID UNTIL</th><th>STATUS</th><th /></tr></thead>
          <tbody>
            {created && <tr><td><strong className="table-primary">QUO-0013</strong><small className="table-secondary">Created just now</small></td><td>Example Shop</td><td>Growth monthly</td><td>Oct 31, 2026</td><td>Nov 14, 2026</td><td><Status>draft</Status></td><td><button className="row-more" aria-label="Quotation actions"><Icon name="more" size={16} /></button></td></tr>}
            <tr><td><strong className="table-primary">QUO-0012</strong><small className="table-secondary">SUB-0012</small></td><td>Example Shop</td><td>Growth monthly</td><td>Oct 16, 2026</td><td>Oct 30, 2026</td><td><Status tone="quotation">Sent</Status></td><td><button className="row-more" aria-label="Quotation actions"><Icon name="more" size={16} /></button></td></tr>
            <tr><td><strong className="table-primary">QUO-0011</strong><small className="table-secondary">SUB-0010</small></td><td>Northstar Studio</td><td>Scale monthly</td><td>Oct 12, 2026</td><td>Oct 26, 2026</td><td><Status tone="active">Accepted</Status></td><td><button className="row-more" aria-label="Quotation actions"><Icon name="more" size={16} /></button></td></tr>
            <tr><td><strong className="table-primary">QUO-0010</strong><small className="table-secondary">SUB-0008</small></td><td>Northstar Studio</td><td>Scale monthly</td><td>Oct 04, 2026</td><td>Oct 18, 2026</td><td><Status tone="expired">Expired</Status></td><td><button className="row-more" aria-label="Quotation actions"><Icon name="more" size={16} /></button></td></tr>
          </tbody>
        </table></div>
      </section>
      <div className="journey-note"><span className="modal-icon"><Icon name="spark" size={18} /></span><div><strong>From quote to recurring revenue</strong><p>When a customer accepts a quotation, activate their subscription and they’ll automatically appear in your next billing preview.</p></div></div>
    </>
  );
}

function Invoices({ invoices, onPayment, onPrint }) {
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
            <td><strong className="table-primary">{invoice.number}</strong><small className="table-secondary">{invoice.subscription}</small></td>
            <td>{invoice.customer_name}</td><td>{shortDate(invoice.issued_on)}</td><td>{shortDate(invoice.due_on)}</td>
            <td><strong>{money(invoice.total_paise)}</strong><small className="table-secondary">{invoice.balance_paise > 0 ? `${money(invoice.balance_paise)} due` : "Paid in full"}</small></td>
            <td><Status tone={invoice.balance_paise === 0 ? "paid" : invoice.is_overdue ? "overdue" : "confirmed"}>{invoice.balance_paise === 0 ? "Paid" : invoice.is_overdue ? "Overdue" : invoice.paid_paise ? "Partial" : invoice.status}</Status></td>
            <td>{invoice.balance_paise > 0 ? <button className="table-action-link" onClick={() => onPayment(invoice)}>Record payment</button> : <button className="row-more" aria-label={`Print ${invoice.number}`} onClick={() => window.print()}><Icon name="download" size={16} /></button>}</td>
          </tr>)}</tbody>
        </table></div> : <div className="table-empty"><span className="empty-check"><Icon name="search" /></span><div><strong>No invoices found</strong><small>Try adjusting your search.</small></div></div>}
      </section>
    </>
  );
}

function Catalog({ onCreate }) {
  return (
    <>
      <PageHeader eyebrow="YOUR OFFERING" title="Products & plans" subtitle="Keep your catalog tidy and your subscription plans clear." action={<Button kind="primary" icon="plus" onClick={onCreate}>Add to catalog</Button>} />
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>Products & add-ons</h2><span>Services and one-time items customers can add</span></div><button className="subtle-link" onClick={onCreate}>Manage products <Icon name="chevron" size={14} /></button></div>
        <div className="catalog-grid">{productRows.map((product) => <article className="catalog-item" key={product.name}>
          <span className={`product-icon ${product.color}`}>{product.icon}</span><div className="catalog-main"><div className="catalog-topline"><strong>{product.name}</strong><Status tone="active">{product.state}</Status></div><p>{product.detail}</p><small>{product.type}</small></div><strong className="catalog-price">{money(product.price)}</strong>
        </article>)}</div>
      </section>
      <section className="content-card list-card plans-card">
        <div className="list-toolbar"><div><h2>Subscription plans</h2><span>Recurring pricing your customers can count on</span></div><Button onClick={onCreate} icon="plus">Add plan</Button></div>
        <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>PLAN</th><th>BILLING</th><th>BASE PRICE</th><th>SUBSCRIBERS</th><th>STATUS</th><th /></tr></thead>
          <tbody>{planRows.map((plan) => <tr key={plan.name}><td><strong className="table-primary">{plan.name}</strong></td><td>{plan.cadence}</td><td><strong>{money(plan.price)}</strong></td><td>{plan.subscribers}</td><td><Status tone="active">{plan.state}</Status></td><td><button className="row-more" aria-label={`Edit ${plan.name}`}><Icon name="more" size={16} /></button></td></tr>)}</tbody>
        </table></div>
      </section>
    </>
  );
}

function Customers({ invoices, onAdd, onCustomer }) {
  return (
    <>
      <PageHeader eyebrow="PEOPLE & RELATIONSHIPS" title="Customers" subtitle="Your customer relationships, subscriptions, and balances." action={<Button kind="primary" icon="plus" onClick={onAdd}>Add customer</Button>} />
      <section className="content-card list-card">
        <div className="list-toolbar"><div><h2>All customers</h2><span>{customers.length} customers</span></div><button className="select-chip">All customers <span>⌄</span></button></div>
        <div className="table-scroll"><table className="data-table full-table">
          <thead><tr><th>CUSTOMER</th><th>SUBSCRIPTIONS</th><th>OPEN BALANCE</th><th>STATUS</th><th /></tr></thead>
          <tbody>{customers.map((customer) => <tr key={customer.name}>
            <td><span className="customer-cell"><span className={`customer-avatar ${customer.color}`}>{customer.initials}</span><span><strong className="table-primary">{customer.name}</strong><small className="table-secondary">{customer.email}</small></span></span></td>
            <td>{customer.subs} subscription</td><td><strong>{money(invoices.filter((invoice) => invoice.customer_name === customer.name).reduce((sum, invoice) => sum + invoice.balance_paise, 0))}</strong></td><td><Status tone="active">Active</Status></td><td><button className="row-more" onClick={onCustomer} aria-label={`Open ${customer.name} customer portal`}><Icon name="chevron" size={16} /></button></td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <div className="portal-promo"><div><span className="modal-icon"><Icon name="users" /></span><span><strong>Give customers a place of their own</strong><small>Switch to the customer view to see subscriptions and invoices from their perspective.</small></span></div><Button kind="primary" onClick={onCustomer}>Preview customer portal</Button></div>
    </>
  );
}

function CustomerPortal({ subscriptions, invoices, onAction, onPay, onInvoice }) {
  const activeSubscription = subscriptions[0];
  return (
    <>
      <div className="portal-welcome"><div className="portal-avatar">E</div><div><p className="eyebrow">WELCOME BACK</p><h1>Good morning, Example Shop</h1><p>Here’s your subscription at a glance.</p></div><span className="portal-tag"><span /> CUSTOMER PORTAL</span></div>
      {activeSubscription ? <>
        <section className="portal-subscription">
          <div className="portal-sub-header"><div><span className="eyebrow">YOUR SUBSCRIPTION</span><Status tone={activeSubscription.status}>{activeSubscription.status}</Status></div><button className="row-more" aria-label="Subscription options"><Icon name="more" /></button></div>
          <h2>{activeSubscription.plan}</h2><p className="portal-sub-number">{activeSubscription.number} · Started {shortDate(activeSubscription.start_date)}</p>
          <div className="portal-sub-stats"><div><small>Monthly total</small><strong>{money(activeSubscription.mrr_paise)}</strong></div><div><small>Next billing date</small><strong>{shortDate(activeSubscription.next_bill_date)}</strong></div><div><small>Includes</small><strong>Odoo integration</strong><small>₹560.00 add-on</small></div></div>
          <div className="portal-actions">{activeSubscription.permitted_actions.map((action) => <Button key={action} onClick={() => onAction(activeSubscription.id, action)}>{action === "close" ? "Cancel subscription" : action[0].toUpperCase() + action.slice(1)}</Button>)}</div>
        </section>
        <section className="content-card list-card portal-invoices">
          <div className="list-toolbar"><div><h2>Your invoices</h2><span>Access billing history and payments</span></div><button className="subtle-link" onClick={onInvoice}>View all <Icon name="chevron" size={14} /></button></div>
          {invoices.length ? <div className="table-scroll"><table className="data-table full-table">
            <thead><tr><th>INVOICE</th><th>ISSUED</th><th>AMOUNT</th><th>STATUS</th><th /></tr></thead>
            <tbody>{invoices.map((invoice) => <tr key={invoice.id}><td><strong className="table-primary">{invoice.number}</strong><small className="table-secondary">Due {shortDate(invoice.due_on)}</small></td><td>{shortDate(invoice.issued_on)}</td><td><strong>{money(invoice.total_paise)}</strong><small className="table-secondary">{invoice.balance_paise > 0 ? `${money(invoice.balance_paise)} remaining` : "Paid in full"}</small></td><td><Status tone={invoice.balance_paise === 0 ? "paid" : invoice.paid_paise ? "partial" : invoice.status}>{invoice.balance_paise === 0 ? "Paid" : invoice.paid_paise ? "Partial" : "Due"}</Status></td><td>{invoice.balance_paise > 0 ? <button className="table-action-link" onClick={() => onPay(invoice.id)}>Pay invoice</button> : <button className="row-more" aria-label="View invoice" onClick={onInvoice}><Icon name="download" size={16} /></button>}</td></tr>)}</tbody>
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

export default App;
