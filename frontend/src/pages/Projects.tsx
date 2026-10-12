import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiBaseUrl, getCsrfToken, request } from "../api/client";
import { api } from "../api/jobs";

type Project = { id: string; name: string; description: string; status: string; framework: string | null; source_revision: string | null; uploaded_at: string | null };
type Scan = { id: string; project_id: string; status: string; framework: string; languages: string[]; file_count: number; finding_count?: number; reason: string; created_at: string };
const finding = { id: "BOLA-001", type: "BROKEN_OBJECT_LEVEL_AUTHORIZATION", severity: "HIGH" as const,
  file_path: "app/access.py", description: "A user can access another user's private document through get_document." };

function upload(projectId: string, file: File, progress: (value: number) => void): Promise<Project> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiBaseUrl}/api/projects/${encodeURIComponent(projectId)}/${file.name.toLowerCase().endsWith(".zip") ? "upload" : "upload-file"}`);
    xhr.withCredentials = true; xhr.timeout = 120000;
    xhr.setRequestHeader("Content-Type", file.name.toLowerCase().endsWith(".zip") ? "application/zip" : "text/plain"); xhr.setRequestHeader("X-CSRF-Token", getCsrfToken()); xhr.setRequestHeader(file.name.toLowerCase().endsWith(".zip") ? "X-Archive-Name" : "X-File-Name", file.name);
    xhr.upload.onprogress = event => { if (event.lengthComputable) progress(Math.round(event.loaded / event.total * 100)); };
    xhr.onload = () => { try { const value = JSON.parse(xhr.responseText); if (xhr.status >= 200 && xhr.status < 300) resolve(value); else reject(new Error(value.detail || `Upload failed (${xhr.status})`)); } catch { reject(new Error("Upload returned an invalid response")); } };
    xhr.onerror = () => reject(new Error("Upload failed: API unavailable"));
    xhr.ontimeout = () => reject(new Error("Upload timed out"));
    xhr.send(file);
  });
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [source, setSource] = useState<{ path: string; content: string } | null>(null);
  const [name, setName] = useState(""); const [description, setDescription] = useState(""); const [zip, setZip] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState(0); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  async function refresh() { const rows = await request<Project[]>("/api/projects"); setProjects(rows); if (selected) setSelected(rows.find(row => row.id === selected.id) || null); }
  useEffect(() => { void refresh().catch(e => setError(e instanceof Error ? e.message : "Could not load projects")); }, []);
  async function useDemoRepository() {
    setError(""); setMessage("");
    try {
      const response = await fetch("/sentinel-bola-demo.zip");
      if (!response.ok) throw new Error("Demo repository ZIP is unavailable.");
      const archive = await response.blob();
      fileInput.current && (fileInput.current.value = "");
      setZip(new File([archive], "sentinel-bola-demo.zip", { type: "application/zip" }));
      if (!name.trim()) setName("SENTINEL-X BOLA demo");
      setMessage("Demo repository selected. Upload it to run the supported BOLA workflow.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the demo repository."); }
  }
  async function create() {
    if (!zip) { setError("Select a ZIP or source file first."); return; }
    setBusy(true); setError(""); setMessage(""); setProgress(0);
    try {
      const project = await request<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name, description }) });
      const imported = await upload(project.id, zip, setProgress);
      setSelected(imported); setZip(null); setName(""); setDescription(""); await refresh();
      setMessage(imported.status === "SUPPORTED_BOLA_CONTRACT" ? "BOLA example uploaded. Static scanning and protected remediation are available." : imported.status === "READY_FOR_SCAN" ? "Source uploaded. Start a static security scan to review potential findings." : "Uploaded format has no supported analysis language.");
      setFiles(await request<string[]>(`/api/projects/${project.id}/files`));
    } catch (e) { setError(e instanceof Error ? e.message : "Project upload failed"); await refresh(); }
    finally { setBusy(false); }
  }
  async function select(project: Project) {
    setSelected(project); setSource(null); setError("");
    try { setFiles(await request<string[]>(`/api/projects/${project.id}/files`)); setScans(await request<Scan[]>(`/api/projects/${project.id}/scans`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load files"); }
  }
  async function startScan() {
    if (!selected) return; setBusy(true); setError("");
    try { const result = await request<Scan>(`/api/projects/${selected.id}/scan`, { method: "POST" }, 30000);
      setScans(await request<Scan[]>(`/api/projects/${selected.id}/scans`));
      setMessage(result.status === "UNSUPPORTED" ? result.reason : `Scan complete: ${result.finding_count || 0} potential findings. Review them on the Findings page.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Scan failed"); } finally { setBusy(false); }
  }
  async function startFinding() {
    if (!selected) return;
    setBusy(true); setError("");
    try { const result = await api.createFinding({ target_app_id: selected.id, finding });
      setMessage(`Finding supplied and AI remediation started. Job ${result.job_id}`); window.location.assign(`/jobs/${result.job_id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not start remediation"); }
    finally { setBusy(false); }
  }
  return <div className="page"><div className="page-heading"><div><div className="eyebrow">SOURCE ONBOARDING</div><h1>Projects</h1><p>Upload a ZIP repository or source file, run a static scan, and review potential findings.</p></div></div>
    <section className="panel create-panel"><div className="panel-heading"><h2>New Project → Upload Repository</h2></div>
      <div className="project-form">
        <label>Project name<input value={name} maxLength={100} onChange={e => setName(e.target.value)} placeholder="My FastAPI project" /></label>
        <label>Description<input value={description} maxLength={1000} onChange={e => setDescription(e.target.value)} placeholder="Optional" /></label>
        <label className="project-field-archive">Repository ZIP or source file<input ref={fileInput} type="file" accept=".zip,.py,.js,.jsx,.ts,.tsx" onChange={e => { setZip(e.target.files?.[0] || null); setMessage(""); setError(""); }} /></label>
        <div className="project-form-actions">
          <button className="button button-primary" disabled={busy || !name.trim() || !zip} onClick={() => void create()}>Upload Repository</button>
          <button className="button button-secondary" disabled={busy} onClick={() => void useDemoRepository()}>Use demo repository</button>
          <a className="project-demo-link" href="/sentinel-bola-demo.zip" download>Download demo ZIP</a>
        </div>
        {zip && <p className="project-file-name" role="status">Selected: {zip.name}</p>}
        {busy && <p className="project-file-name" role="status">Upload progress: {progress}%</p>}
        {!name.trim() || !zip ? <p className="project-file-hint">Enter a project name and choose a ZIP or source file to enable upload.</p> : null}
        <p className="fine-print">Static scans never execute uploaded code. Findings are potential matches requiring review. The BOLA demo has a separate protected remediation workflow. Source is never sent to AI during upload or static scan.</p>
      </div>
    </section>
    {error && <div className="error-banner" role="alert">{error}</div>}{message && <div className="notice wide" role="status">{message}</div>}
    <section className="panel"><div className="panel-heading"><h2>Your projects</h2><button className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>
      {projects.length === 0 ? <p>No projects uploaded yet.</p> : projects.map(project => <button key={project.id} className="button button-secondary" style={{ margin: 6 }} onClick={() => void select(project)}>{project.name} · {project.status}</button>)}
    </section>
    {selected && <section className="panel"><div className="panel-heading"><h2>{selected.name}</h2><span>{selected.status}</span></div>
      <p>{selected.description}</p><p>Framework: {selected.framework || "Pending detection"}</p><p>Source revision: <code>{selected.source_revision || "Unavailable"}</code></p>
      <button className="button button-primary" disabled={busy || selected.status === "UNSUPPORTED"} onClick={() => void startScan()}>Start static security scan</button>
      <h3>Scan history</h3>{scans.length ? scans.map(scan => <p key={scan.id}><strong>{scan.status}</strong> · {scan.framework} · {scan.created_at} · <Link to="/findings">View findings</Link><br/>{scan.reason}</p>) : <p>No scans yet.</p>}
      {selected.status === "SUPPORTED_BOLA_CONTRACT" ? <><p>Supported finding: Broken Object Level Authorization in <code>app/access.py</code>. Confirm this finding applies to a repository you are authorized to test.</p>
        <button className="button button-primary" disabled={busy} onClick={() => void startFinding()}>Select BOLA finding and generate AI fix</button></> : <p>General static findings can be reviewed after scanning. Automated patch verification currently supports only the BOLA example.</p>}
      <h3>Source files</h3>{files.map(path => <button key={path} className="button button-secondary" style={{ margin: 4 }} onClick={() => void request<{path:string;content:string}>(`/api/projects/${selected.id}/files/${path.split("/").map(encodeURIComponent).join("/")}`).then(setSource).catch(e => setError(e.message))}>{path}</button>)}
      {source && <div><h4>{source.path}</h4><pre style={{ overflow: "auto", maxHeight: 420 }}>{source.content}</pre></div>}
      <p><Link to="/findings">View security findings</Link></p>
    </section>}
  </div>;
}
