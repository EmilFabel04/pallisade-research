# TradingAgents — Web UI

A browser-based research console wrapping the `TradingAgents` Python framework.
Two services:

| Service | Purpose | Port |
|---|---|---|
| `web/api` (FastAPI) | wraps `TradingAgentsGraph`, streams agent progress as SSE | `8000` |
| `web/ui` (Next.js 15) | research-console UI (App Router + Tailwind v4) | `3000` |

The UI is positioned as a **research dossier tool for professional analysts**.
The internal BUY/SELL/HOLD verdict from the Portfolio Manager is **hidden by
default** and only surfaced via an explicit reveal, with a non-advice notice. See
the SA FAIS rationale in the project chat history.

## Prerequisites

- The `tradingagents` conda env (Python 3.13) with the package installed:
  ```bash
  conda activate tradingagents
  pip install .                      # from repo root, if not done yet
  pip install -r web/api/requirements.txt
  ```
- Node.js 20+ and npm.
- LLM provider keys exported (e.g. `OPENAI_API_KEY=...`) or a `.env` at repo root.

## First-time setup

```bash
# 1. API deps (FastAPI on top of the existing tradingagents env)
conda activate tradingagents
pip install -r web/api/requirements.txt

# 2. UI deps
cd web/ui
npm install
cd -
```

## Run (two terminals)

**Terminal 1 — API:**
```bash
conda activate tradingagents
uvicorn web.api.main:app --reload --port 8000
```

**Terminal 2 — UI:**
```bash
cd web/ui
npm run dev
```

Open <http://localhost:3000>.

The Next.js dev server proxies `/api/*` to the FastAPI server (see
`next.config.mjs`), so the browser only sees one origin.

## Endpoints

| Method | Path | What |
|---|---|---|
| `POST` | `/runs` | Queue a run. Body: `{ticker, trade_date, analysts, asset_type, llm_provider?, ...}`. Returns `{run_id}`. |
| `GET`  | `/runs` | List all runs (in-memory). |
| `GET`  | `/runs/:id` | Run metadata + reports collected so far. |
| `GET`  | `/runs/:id/stream` | Server-Sent Events stream: `status`, `report`, `done`, `error`. |
| `GET`  | `/healthz` | Liveness probe. |

## v0 limitations (intentional)

- **In-memory run store** — runs are lost when the API restarts. Add Postgres
  or SQLite when you need persistence beyond a session.
- **No auth, no billing, no multi-tenancy** — single user, localhost.
- **No queue** — runs execute in background threads inside the API process.
  For >1 concurrent paid user, swap in Celery/RQ + Redis.
- **No per-user API keys** — uses whatever LLM keys are in the API process's
  environment.

These are the four things to fix before billing customers. The "not an FSP"
product framing (B2B gating, no recommendation in the headline UI) is already
in place in the markup.

## Project structure

```
web/
├── api/
│   ├── main.py            FastAPI app
│   └── requirements.txt
└── ui/
    ├── app/
    │   ├── layout.tsx          shell + non-advice footer
    │   ├── globals.css         design tokens + prose styles
    │   ├── page.tsx            new-run form
    │   └── runs/
    │       ├── page.tsx        run history
    │       └── [id]/page.tsx   live dossier + SSE consumer
    ├── next.config.mjs
    ├── package.json
    └── tsconfig.json
```
