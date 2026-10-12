import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { request } from "../api/client";

type Ready = { status: string; [key:string]: unknown };
type AiReady = { configured: boolean; source_sharing: string; status: string };
type Observability = { configured: boolean; hosted_delivery_verified: boolean; local_workflow_events: boolean };
export default function Settings() {
  const [me,setMe]=useState<{user:{email:string}}|null>(null);
  const [ai,setAi]=useState<AiReady|null>(null);
  const [obs,setObs]=useState<Observability|null>(null);
  const [ready,setReady]=useState<Ready|null>(null);
  const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  async function refresh() {setLoading(true);setError("");try {const [identity,provider,telemetry,health]=await Promise.all([request<{user:{email:string}}>("/api/auth/me"),request<AiReady>("/api/ai/readiness"),request<Observability>("/api/observability/status"),request<Ready>("/ready").catch(() => ({status:"not ready"} as Ready))]);setMe(identity);setAi(provider);setObs(telemetry);setReady(health);}catch(e){setError(e instanceof Error?e.message:"Could not load settings");}finally{setLoading(false);}}
  useEffect(()=>{void refresh();},[]);
  return <div className="page"><div className="page-heading"><div><div className="eyebrow">WORKSPACE HEALTH</div><h1>Settings</h1><p>View account and integration readiness without exposing server secrets.</p></div><button className="button button-secondary" onClick={()=>void refresh()} disabled={loading}><RefreshCw size={15}/> Refresh</button></div>
    {error&&<div className="error-banner" role="alert">{error}</div>}
    {loading?<div className="loading-state">Loading settings…</div>:<div className="dashboard-grid"><section className="panel" style={{padding:20}}><h2>Account</h2><p>Signed in as <strong>{me?.user.email||"Unavailable"}</strong>.</p><button className="button button-secondary" onClick={()=>window.dispatchEvent(new Event("sentinel-disconnect"))}>Log out</button></section><section className="panel" style={{padding:20}}><h2>Backend</h2><p>Readiness: <strong>{ready?.status||"Unavailable"}</strong></p><p>The API, model planner and verifier readiness are reported by the backend health probe.</p></section><section className="panel" style={{padding:20}}><h2>AI Security Analysis</h2><p>Server configuration: <strong>{ai?.status||"Unavailable"}</strong></p><p>{ai?.source_sharing||"Source-sharing status unavailable."} Model access and quota are checked at request time. The key remains server-side.</p></section><section className="panel" style={{padding:20}}><h2>Observability</h2><p>Neatlogs key: <strong>{obs?.configured?"Configured":"Not configured"}</strong></p><p>Hosted delivery: {obs?.hosted_delivery_verified?"Verified":"Not verified in this run"}. Local workflow records: {obs?.local_workflow_events?"Available":"Unavailable"}.</p></section></div>}
  </div>;
}
