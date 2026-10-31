import { useState } from "react";

export default function Auth({ onLogin, busy, error }) {
  const [mode, setMode] = useState("login");
  const [formError, setFormError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setFormError("");
    const values = new FormData(event.currentTarget);
    const data = Object.fromEntries(values.entries());
    try {
      await onLogin(mode, data);
    } catch (requestError) {
      setFormError(requestError.message);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <a className="auth-brand" href="/" aria-label="Brightloop home">
          <span className="brand-mark"><span /></span>
          <span>brightloop<span className="brand-dot">.</span></span>
        </a>
        <p className="eyebrow">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</p>
        <h1>{mode === "login" ? "Sign in to your workspace" : "Create your customer account"}</h1>
        <p className="auth-subtitle">
          {mode === "login"
            ? "Manage subscriptions, billing, and customer relationships."
            : "Create an account to view your Brightloop subscriptions and invoices."}
        </p>
        {(formError || error) && <div className="api-alert auth-alert" role="alert">{formError || error}</div>}
        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && <>
            <label htmlFor="full-name">Full name</label>
            <input id="full-name" name="full_name" autoComplete="name" required maxLength={200} />
            <label htmlFor="company-name">Company name <span>Optional</span></label>
            <input id="company-name" name="company_name" autoComplete="organization" maxLength={200} />
          </>}
          <label htmlFor="email">Email address</label>
          <input id="email" name="email" type="email" autoComplete="email" required maxLength={254} />
          <label htmlFor="password">Password</label>
          <input id="password" name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required />
          <button className="button button-primary auth-submit" disabled={busy} type="submit">
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? "New to Brightloop?" : "Already have an account?"}
          <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setFormError(""); }}>
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </section>
    </main>
  );
}
