# neatHack 2026 — Official Project Submission Dossier

---

## 📌 Executive Summary

| Submission Field | Official Entry Value |
| :--- | :--- |
| **Project Name** | **SENTINEL-X** |
| **Track Category** | **Best Use of Entire (Checkpoints & Session Provenance)** |
| **Primary Checkpoint ID** | `01M4N94JE9XCAZ641XEQ65A3ZG` |
| **Secondary Checkpoint IDs** | `01M4N9MJP3YZTR3Q8WY5NGQF38`, `01M4NAQQ8GVMQKK3JCY2HVZY04` |
| **Commit SHA** | `254fdac2b2b858e5c8adab6361f9553e4e7d44d5` |
| **Entire Live Proof Link** | [https://entire.io/gh/rudrapaliwal-1/neatlog/commit/254fdac2b2b858e5c8adab6361f9553e4e7d44d5](https://entire.io/gh/rudrapaliwal-1/neatlog/commit/254fdac2b2b858e5c8adab6361f9553e4e7d44d5) |
| **Entire Secondary Link** | [https://entire.io/gh/rudrapaliwal-1/neatlog/commit/2f12c70f72ff81df81039260793ae55842ca9811](https://entire.io/gh/rudrapaliwal-1/neatlog/commit/2f12c70f72ff81df81039260793ae55842ca9811) |
| **Public GitHub Repository** | [https://github.com/rudrapaliwal-1/neatlog](https://github.com/rudrapaliwal-1/neatlog) |
| **Team Repository** | [https://github.com/Kartikeysharma1105/Agent-Solution-](https://github.com/Kartikeysharma1105/Agent-Solution-) |

---

## 🎯 What is SENTINEL-X?

**SENTINEL-X** is an autonomous AI-assisted vulnerability patching, verification, and audit gate engine. It bridges the critical trust gap in automated software security:
1. **Automated Discovery**: Scans target codebases for security vulnerabilities (such as Broken Object Level Authorization - BOLA, injection, and privilege escalation).
2. **AI Patch Synthesis**: Leverages LLM reasoning agents to propose minimal, precise security patches.
3. **Zero-Trust Human Approval Gate**: Cryptographically binds patch proposals to exact SHA-256 hashes—no unapproved code enters verification or production.
4. **Isolated Docker Verification Sandbox**: Automatically spins up clean Docker containers running protected test suites to prove that patches resolve vulnerabilities without introducing regressions.
5. **Entire Provenance Tracking**: Deeply integrated with **Entire CLI**, recording complete AI agent interaction traces, diffs, and developer intent into permanent, tamper-resistant git checkpoint references.

---

## 🚀 How SENTINEL-X Uses Entire CLI (Best Use of Entire Track)

Unlike typical AI tools whose internal reasoning and modifications vanish into ephemeral chat history, SENTINEL-X treats Entire as its **definitive source of provenance**:

### 1. Antigravity Agent Lifecycle Hooks
- Integrates Entire CLI `0.11.4` hooks (`PreInvocation`, `PreToolUse`, `Stop`) into `.agents/hooks.json`.
- Every terminal command, prompt, and tool invocation is recorded during active coding sessions.

### 2. Live Git Checkpoints (`refs/entire/checkpoints/*`)
- Checkpoints are linked to git commit trailers:
  - `Entire-Checkpoint: 01M4N94JE9XCAZ641XEQ65A3ZG`
  - `Entire-Checkpoint: 01M4N9MJP3YZTR3Q8WY5NGQF38`
  - `Entire-Checkpoint: 01M4NAQQ8GVMQKK3JCY2HVZY04`
- References are preserved in Git under `refs/entire/checkpoints/` and pushed to remote repositories for public verification.

### 3. Public Verification Proof
- Live inspection is verified on the Entire platform:
  👉 **[https://entire.io/gh/rudrapaliwal-1/neatlog/commit/254fdac2b2b858e5c8adab6361f9553e4e7d44d5](https://entire.io/gh/rudrapaliwal-1/neatlog/commit/254fdac2b2b858e5c8adab6361f9553e4e7d44d5)**
- Judges can inspect:
  - The exact user intents and agent tool calls.
  - Granular code diffs captured across checkpoints.
  - Complete execution logs and session timelines.

---

## 🏗️ Architecture & Core Components

```
┌─────────────────┐       ┌────────────────────┐       ┌──────────────────────┐
│  React Frontend │ ────> │ FastAPI Backend    │ ────> │  AI Patch Generator  │
│  (Vite + TS)    │       │ (Auth + Audit Log) │       │  (Qwen / Multi-Agent)│
└─────────────────┘       └────────────────────┘       └──────────────────────┘
                                    │                             │
                                    ▼                             ▼
                          ┌────────────────────┐       ┌──────────────────────┐
                          │ SHA-256 Approval   │ ────> │ Isolated Docker      │
                          │ Gate Enforcement   │       │ Verifier Sandbox     │
                          └────────────────────┘       └──────────────────────┘
                                    │
                                    ▼
                          ┌────────────────────┐
                          │ Entire CLI Tracker │ ────> refs/entire/checkpoints/*
                          │ (Session Checkpoint│       entire.io Public Proof
                          └────────────────────┘
```

---

## 🧪 Verification & Test Suite Results

- **Unit & Integration Tests**: 196 tests passed (0 failures, 0 skipped).
- **Docker Verification**: Verified against BOLA contracts with 8/8 tests passing in isolated containers.
- **Frontend Build**: Clean TypeScript compilation and Vite production build.
- **Security Audit**: All credentials excluded via `.gitignore`; safe for public evaluation.

---

## 💻 Quickstart (How to Run SENTINEL-X)

### Prerequisites
- Python 3.11+
- Node.js 18+ / pnpm
- Docker Engine
- Entire CLI (`0.11.4+`)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# Activate environment:
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
pnpm install
pnpm dev
```

### 3. Check Entire CLI Status
```bash
entire status
entire checkpoint list
```

---

## 👥 Submission Contact
- **Project Lead**: Rudra Paliwal (`rudrapaliwal51206@gmail.com`)
- **Submission Target**: neatHack 2026
- **Date**: October 12, 2026
