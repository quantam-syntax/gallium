import { useState } from "react";

export default function Auth({ onLogin, onPasswordResetRequest, onPasswordResetConfirm, onExitReset, resetContext, busy, error, successNotice }) {
  const [mode, setMode] = useState(resetContext ? "reset" : "login");
  const [formError, setFormError] = useState("");
  const [resetRequested, setResetRequested] = useState(false);

  const titles = {
    login: "Sign in to your workspace",
    register: "Create your customer account",
    forgot: "Reset your password",
    reset: "Choose a new password",
  };

  async function submit(event) {
    event.preventDefault();
    setFormError("");
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      if (mode === "forgot") {
        await onPasswordResetRequest(data.email);
        setResetRequested(true);
      } else if (mode === "reset") {
        if (data.password !== data.confirm_password) {
          setFormError("The passwords do not match.");
          return;
        }
        await onPasswordResetConfirm({ ...resetContext, password: data.password });
        setMode("login");
      } else {
        await onLogin(mode, data);
      }
    } catch (requestError) {
      setFormError(requestError.message);
    }
  }

  const resetLinkValid = Boolean(resetContext?.uid && resetContext?.token);
  const isResetFlow = mode === "forgot" || mode === "reset";

  return (
    <main className="auth-page">
      <section className="auth-card">
        <a className="auth-brand" href="/" aria-label="Brightloop home">
          <span className="brand-mark"><span /></span>
          <span>brightloop<span className="brand-dot">.</span></span>
        </a>
        <p className="eyebrow">{mode === "login" ? "WELCOME BACK" : mode === "register" ? "GET STARTED" : "ACCOUNT SECURITY"}</p>
        <h1>{titles[mode]}</h1>
        <p className="auth-subtitle">
          {mode === "login"
            ? "Manage subscriptions, billing, and customer relationships."
            : mode === "register"
              ? "Create an account to view your Brightloop subscriptions and invoices."
              : mode === "forgot"
                ? resetRequested
                  ? "If an account exists for that address, password-reset instructions are on their way."
                  : "Enter your email and we’ll send password-reset instructions if an account exists."
                : resetLinkValid
                  ? "Choose a new password. You’ll sign in again after the password has been updated."
                  : "This password-reset link is incomplete. Request a new reset email and use its full link."}
        </p>
        {(formError || error) && <div className="api-alert auth-alert" role="alert">{formError || error}</div>}
        {successNotice && <div className="auth-success" role="status">{successNotice}</div>}
        {mode === "reset" && !resetLinkValid
          ? <button className="button button-primary auth-submit" type="button" onClick={() => { onExitReset(); setMode("forgot"); setFormError(""); setResetRequested(false); }}>Request a new reset link</button>
          : <form className="auth-form" onSubmit={submit}>
            {mode === "register" && <>
              <label htmlFor="full-name">Full name</label>
              <input id="full-name" name="full_name" autoComplete="name" required maxLength={200} />
              <label htmlFor="company-name">Company name <span>Optional</span></label>
              <input id="company-name" name="company_name" autoComplete="organization" maxLength={200} />
            </>}
            {(mode === "login" || mode === "register" || mode === "forgot") && <>
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" required maxLength={254} />
            </>}
            {(mode === "login" || mode === "register") && <>
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required />
            </>}
            {mode === "reset" && <>
              <label htmlFor="password">New password</label>
              <input id="password" name="password" type="password" autoComplete="new-password" minLength="10" required />
              <label htmlFor="confirm-password">Confirm new password</label>
              <input id="confirm-password" name="confirm_password" type="password" autoComplete="new-password" minLength="10" required />
            </>}
            {mode === "forgot" && resetRequested
              ? <button className="button auth-submit" type="button" onClick={() => { setResetRequested(false); setFormError(""); }}>Send another email</button>
              : <button className="button button-primary auth-submit" disabled={busy} type="submit">
                {busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : mode === "forgot" ? "Send reset instructions" : "Update password"}
              </button>}
          </form>}
        {!isResetFlow && <p className="auth-switch">
          {mode === "login" ? "New to Brightloop?" : "Already have an account?"}
          <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setFormError(""); }}>
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>}
        {mode === "login" && <button className="auth-forgot" type="button" onClick={() => { setMode("forgot"); setFormError(""); setResetRequested(false); }}>Forgot your password?</button>}
        {isResetFlow && <button className="auth-back" type="button" onClick={() => { onExitReset(); setMode("login"); setFormError(""); setResetRequested(false); }}>Back to sign in</button>}
      </section>
    </main>
  );
}
