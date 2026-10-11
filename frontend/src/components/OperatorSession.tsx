import { useEffect, useState, type ReactNode } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { api } from "../api/jobs";
import { apiBaseUrl, setOperatorToken } from "../api/client";

export default function OperatorSession({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const disconnect = () => { setOperatorToken(""); setConnected(false); setError(""); };
    window.addEventListener("sentinel-disconnect", disconnect);
    return () => window.removeEventListener("sentinel-disconnect", disconnect);
  }, []);
  async function connect() {
    if (busy) return;
    setBusy(true); setError(""); setOperatorToken(token);
    try { await api.jobs(); setConnected(true); setToken(""); }
    catch (e) { setOperatorToken(""); setError(e instanceof Error ? e.message : "Connection failed"); }
    finally { setBusy(false); }
  }
  if (connected) return <>{import.meta.env.VITE_EXECUTION_LABEL && <div className="fixture-banner" role="status">{import.meta.env.VITE_EXECUTION_LABEL}</div>}{children}</>;
  return <main className="operator-connect"><section className="panel operator-card">
    <div className="eyebrow">{import.meta.env.VITE_EXECUTION_LABEL || "TEAM BEYONDSIGHT / LIVE ENGINE"}</div>
    <h1>SENTINEL<span className="text-cyan">-X</span></h1>
    <h2>Connect your workspace</h2>
    <p>Review AI proposals, authorize an exact patch, and inspect independent verification evidence.</p>
    <form onSubmit={event => { event.preventDefault(); void connect(); }}>
      <label htmlFor="operator-token">Operator token</label>
      <input id="operator-token" type="password" value={token} onChange={event => setToken(event.target.value)}
        autoComplete="off" spellCheck={false} required minLength={32} maxLength={256} placeholder="Enter the token from your backend session" />
      {error && <div className="error-banner" role="alert">{error}</div>}
      <button className="button button-primary" disabled={busy || token.length < 32}>
        {busy ? <RefreshCw size={16} className="spin" /> : <ShieldCheck size={16} />} Connect to backend
      </button>
    </form>
    <p className="fine-print">Your token stays in memory for this tab. Reloading or disconnecting clears it.</p>
    <a className="text-link" href={`${apiBaseUrl}/docs`} target="_blank" rel="noreferrer">Backend API documentation ↗</a>
  </section></main>;
}
