import { useState } from "react";
import { Search, Menu, Sparkles, KeyRound, Check, X, Shield } from "lucide-react";
import { useLocation } from "react-router-dom";
import { getOperatorToken, setOperatorToken, clearOperatorToken, hasOperatorToken } from "../api/client";

const names: Record<string, string> = {
  "/": "Overview",
  "/findings": "Security findings",
  "/investigation": "Investigation",
  "/verification": "Verification",
  "/activity": "Agent activity",
  "/evidence": "Evidence reports",
};

export default function Header({ onMenu }: { onMenu: () => void }) {
  const location = useLocation();
  const title =
    names[location.pathname] ||
    (location.pathname.startsWith("/jobs/") ? "Investigation details" : "SENTINEL-X");

  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenInput, setTokenInput] = useState(getOperatorToken());
  const [savedMsg, setSavedMsg] = useState("");
  const isAuthConfigured = hasOperatorToken();

  function handleSaveToken(e: React.FormEvent) {
    e.preventDefault();
    if (tokenInput.trim()) {
      setOperatorToken(tokenInput.trim());
      setSavedMsg("Operator token set for current session.");
    } else {
      clearOperatorToken();
      setSavedMsg("Operator token cleared.");
    }
    setTimeout(() => {
      setSavedMsg("");
      setShowTokenModal(false);
    }, 1200);
  }

  return (
    <header className="topbar">
      <button className="menu-trigger" onClick={onMenu} aria-label="Toggle navigation">
        <span className="menu-glyph">
          <Menu size={19} />
        </span>
        <span className="menu-word">FIELD GUIDE</span>
      </button>

      <div className="breadcrumbs">
        <span>Workspace</span>
        <span className="crumb-slash">/</span>
        <strong>{title}</strong>
      </div>

      <div className="header-search">
        <Search size={17} />
        <input
          aria-label="Search findings"
          placeholder="Search findings, jobs, patch hashes…"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.currentTarget.value.trim()) {
              window.location.href = `/findings?search=${encodeURIComponent(
                e.currentTarget.value.trim()
              )}`;
            }
          }}
        />
        <span className="search-spark">
          <Sparkles size={14} />
        </span>
      </div>

      <div className="topbar-actions">
        <button
          className="icon-button"
          onClick={() => {
            setTokenInput(getOperatorToken());
            setShowTokenModal(true);
          }}
          title={isAuthConfigured ? "Operator token configured" : "Set operator token"}
          aria-label="Set operator token"
          style={isAuthConfigured ? { borderColor: "#c9ef72", color: "#c9ef72" } : {}}
        >
          <KeyRound size={17} />
          {isAuthConfigured && <i style={{ background: "#c9ef72" }} />}
        </button>

        <div className="avatar" title="Local Security Operator">
          OP
        </div>
      </div>

      {showTokenModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            zIndex: 100,
            display: "grid",
            placeItems: "center",
            padding: "20px",
            backdropFilter: "blur(6px)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowTokenModal(false);
          }}
        >
          <div
            style={{
              background: "#121212",
              border: "1px solid #414141",
              borderRadius: "16px",
              maxWidth: "480px",
              width: "100%",
              padding: "24px",
              boxShadow: "0 20px 40px rgba(0,0,0,0.8)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "16px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Shield size={20} className="text-cyan" />
                <h3 style={{ margin: 0, fontSize: "18px", color: "#fff" }}>
                  Operator Session Authentication
                </h3>
              </div>
              <button
                className="icon-button"
                onClick={() => setShowTokenModal(false)}
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: "12px", color: "#b5b2ab", lineHeight: 1.6, margin: "0 0 16px" }}>
              The backend enforces single-operator authentication for patch approval and verification requests via <code>X-Operator-Token</code>. This token is retained in memory only and is never stored in persistent browser storage.
            </p>

            <form onSubmit={handleSaveToken}>
              <label
                htmlFor="operator-token"
                style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#ffe45e", marginBottom: "6px" }}
              >
                OPERATOR TOKEN (32+ ASCII characters)
              </label>
              <input
                id="operator-token"
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Enter SENTINEL_OPERATOR_TOKEN..."
                style={{
                  width: "100%",
                  padding: "12px",
                  background: "#080808",
                  border: "1px solid #444",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                  marginBottom: "16px",
                }}
              />

              {savedMsg && (
                <div style={{ color: "#c9ef72", fontSize: "12px", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Check size={14} /> {savedMsg}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                {isAuthConfigured && (
                  <button
                    type="button"
                    className="button button-danger-ghost"
                    onClick={() => {
                      clearOperatorToken();
                      setTokenInput("");
                      setSavedMsg("Token cleared.");
                    }}
                  >
                    Clear Token
                  </button>
                )}
                <button type="submit" className="button button-primary">
                  Save to Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}