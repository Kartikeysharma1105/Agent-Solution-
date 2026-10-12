import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { request } from "../api/client";
import { api, verificationFromEvidence } from "../api/jobs";
import type { VerificationResult } from "../api/types";
import { RefreshCw } from "lucide-react";
import { useJobs } from "../hooks/useJobs";
export default function Verification() {
  const {jobs, loading, error, refresh} = useJobs();
  const [runs, setRuns] = useState<Record<string, VerificationResult>>({});
  const [runsLoaded, setRunsLoaded] = useState(false);
  useEffect(() => { let active=true; setRunsLoaded(false); Promise.all(jobs.filter(job=>["VERIFIED","VERIFICATION_FAILED","EXECUTION_ERROR"].includes(String(job.status))).map(async job => { try { const run=verificationFromEvidence(await api.evidence(job.job_id)); return [job.job_id,run] as const; } catch { return [job.job_id,null] as const; } })).then(values=>{if(active){setRuns(Object.fromEntries(values.filter(([,run])=>run!==null)) as Record<string,VerificationResult>);setRunsLoaded(true);}}); return ()=>{active=false;}; }, [jobs]);
  const [patches, setPatches] = useState<{id:string;finding_id:string;project_name:string;category:string;approval_status:string;verification_status:string}[]>([]);
  const [patchError, setPatchError] = useState("");
  async function refreshPatches() { try { setPatches(await request<typeof patches>("/api/scan-patches")); setPatchError(""); } catch(e) { setPatchError(e instanceof Error ? e.message : "Could not load patch checks"); } }
  useEffect(() => {void refreshPatches();}, []);
  return <div className="page"><div className="page-heading"><div><div className="eyebrow">INDEPENDENT CHECKS</div><h1>Verification</h1><p>Review actual protected verification outcomes and open their evidence. General static findings are not independently verified.</p></div><button className="button button-secondary" onClick={() => {void refresh(); void refreshPatches();}} disabled={loading}><RefreshCw size={15}/> Refresh</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <section className="panel" style={{padding:20}}><h2>Verification runs</h2>{loading ? <p>Loading runs…</p> : jobs.length ? jobs.map(job=><div key={job.job_id} style={{padding:"12px 0", borderBottom:"1px solid var(--border, #334)"}}><strong>{job.finding?.id || job.finding_id || job.job_id}</strong> · {job.status}<p>{runs[job.job_id] ? `Tests: ${runs[job.job_id].tests_passed ?? 0} passed, ${runs[job.job_id].tests_failed ?? 0} failed · ${runs[job.job_id].status}` : ["VERIFIED","VERIFICATION_FAILED"].includes(String(job.status)) ? runsLoaded ? "Stored verification evidence unavailable; open the investigation for details." : "Loading stored verification evidence…" : "No completed verification run. Open the investigation to inspect approval and available actions."}</p><Link to={`/jobs/${encodeURIComponent(job.job_id)}`}>Investigation</Link> · <Link to="/evidence">Evidence export</Link></div>) : <p>No remediation jobs or verification runs yet.</p>}</section>
    <section className="panel" style={{padding:20}}><h2>Advisory Python patch checks</h2>{patchError && <p role="alert">{patchError}</p>}{patches.length ? patches.map(p=><p key={p.id}><strong>{p.project_name}</strong> · {p.category} · Approval {p.approval_status} · Check {p.verification_status} · <Link to={`/findings?search=${encodeURIComponent(p.finding_id)}`}>Finding</Link></p>) : <p>No advisory patch checks yet.</p>}<p>Python syntax and static rechecks can return FAILED or INCONCLUSIVE. They never establish VERIFIED.</p></section>
    <section className="panel" style={{padding:20}}><h2>Supported checks</h2><p>The Python document-access BOLA example uses eight protected tests in an isolated verifier. Other uploaded projects can receive advisory Python patch drafts and syntax/static rechecks, which remain INCONCLUSIVE or FAILED; they are not marked VERIFIED.</p></section>
  </div>;
}
