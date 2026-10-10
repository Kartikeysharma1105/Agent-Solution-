import { Link } from "react-router-dom";
import { ArrowUpRight, FileCode2 } from "lucide-react";
import type { Job } from "../api/types";
import StatusBadge from "./StatusBadge";

export default function FindingsTable({ jobs }: { jobs: Job[] }) {
  if (!jobs.length) {
    return (
      <div className="empty-state">
        No jobs returned. Create the predefined BOLA demo finding or submit a security finding to the backend.
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Finding / Job</th>
            <th>Severity</th>
            <th>Source</th>
            <th>Status</th>
            <th>Updated</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const f = job.finding;
            const jobId = job.id || job.job_id || "";
            const findingId = f?.id || job.finding_id || jobId;
            const findingTitle = f?.type ? f.type.replaceAll("_", " ") : job.summary || "Security finding";
            const dateStr = job.updated_at || job.created_at;

            return (
              <tr key={jobId}>
                <td>
                  <div className="finding-cell">
                    <span className="finding-id">{findingId}</span>
                    <strong>{findingTitle}</strong>
                    <small>{jobId}</small>
                  </div>
                </td>
                <td>
                  <span className={`severity ${String(f?.severity || "unknown").toLowerCase()}`}>
                    {f?.severity || "—"}
                  </span>
                </td>
                <td>
                  <div className="file-cell">
                    <FileCode2 size={14} />
                    {f?.file_path || "—"}
                  </div>
                </td>
                <td>
                  <StatusBadge status={job.status} />
                </td>
                <td className="date-cell">
                  {dateStr ? new Date(dateStr).toLocaleString() : "—"}
                </td>
                <td>
                  <Link
                    className="table-action"
                    to={`/jobs/${encodeURIComponent(jobId)}`}
                    aria-label={`Open ${jobId}`}
                  >
                    <ArrowUpRight size={16} />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}