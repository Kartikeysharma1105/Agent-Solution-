import { useMemo } from "react";
import { FileCode2, Plus, Minus, ShieldCheck, ShieldAlert } from "lucide-react";
import type { Patch } from "../api/types";

interface ParsedLine {
  line: string;
  n: number;
  kind: "add" | "remove" | "hunk" | "context";
}

function parseDiff(diffText: string): { lines: ParsedLine[]; additions: number; deletions: number } {
  let additions = 0;
  let deletions = 0;
  const rawLines = diffText.split(/\r?\n/);
  const lines: ParsedLine[] = [];

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i];
    let kind: ParsedLine["kind"] = "context";

    if (line.startsWith("+") && !line.startsWith("+++")) {
      kind = "add";
      additions++;
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      kind = "remove";
      deletions++;
    } else if (line.startsWith("@@")) {
      kind = "hunk";
    }

    lines.push({ line, n: i + 1, kind });
  }

  return { lines, additions, deletions };
}

export default function PatchDiffViewer({ patch }: { patch: Patch | null }) {
  const diffContent = patch?.patch_text || patch?.diff || "";
  const filesList = patch?.files_changed?.length
    ? patch.files_changed
    : ["app/access.py"];

  const { lines, additions, deletions } = useMemo(() => {
    if (!diffContent) return { lines: [], additions: 0, deletions: 0 };
    return parseDiff(diffContent);
  }, [diffContent]);

  if (!patch) {
    return (
      <div className="empty-state">
        No patch proposal is currently available for this job. A patch will appear once planning completes.
      </div>
    );
  }

  const isPolicyPassed = patch.policy_status === "PASSED";

  return (
    <div className="diff-viewer">
      <div className="diff-filebar">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FileCode2 size={15} />
          <strong>{filesList.join(", ")}</strong>
          {patch.policy_status && (
            <span
              style={{
                marginLeft: "8px",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "999px",
                background: isPolicyPassed ? "#172319" : "#32151d",
                color: isPolicyPassed ? "#c9ef72" : "#ff8ca2",
                border: `1px solid ${isPolicyPassed ? "#48602d" : "#773044"}`,
              }}
            >
              {isPolicyPassed ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
              Policy: {patch.policy_status}
            </span>
          )}
        </div>
        <div className="diff-counts">
          <span className="add-text">
            <Plus size={13} />
            {additions} additions
          </span>
          <span className="remove-text">
            <Minus size={13} />
            {deletions} deletions
          </span>
        </div>
      </div>

      {diffContent ? (
        <pre className="diff-code">
          {lines.map((item, i) => (
            <div key={i} className={`diff-line ${item.kind}`}>
              <span className="line-number">{item.n}</span>
              <span className="line-content">{item.line || " "}</span>
            </div>
          ))}
        </pre>
      ) : (
        <div className="empty-state">
          Patch record exists but contains empty diff content.
        </div>
      )}
    </div>
  );
}