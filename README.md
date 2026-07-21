# Pallisade Research

Cited research-intelligence platform for professional analysts. A unified web app
(Research copilot, Debate, Agents, Checks, Watchlist, Dashboard, Artefacts) backed by a
FastAPI service and a durable worker running a multi-agent analysis graph.

Extracted from the original `TradingAgents` monorepo as a clean, research-focused repo:
the deal-evaluation (PE) and Foresight experiments were left behind. Debate and Agents run
on the `tradingagents` graph, which is kept.

## Layout

```
pallisade_research/     cited-answer engine: sources, planner, reconcile, verify, chat
pallisade_connections/  per-org data-source resolver + connectors
pallisade_core/         shared infra: auth, db, settings, documents, RAG, runs
pallisade_worker/       durable job worker (parse, embed, run_debate, check_memo)
tradingagents/          multi-agent debate/analysis graph (powers Debate + Agents)
web/api/                FastAPI app (web.api.main:app)
web/ui/                 Next.js platform UI
alembic/                database migrations
tests/                  pytest suite
```

## Development

Requirements: Python 3.10+, Node 18+, PostgreSQL (with `pgvector`).

```bash
# 1. Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Config — copy the example and fill in the required keys
cp .env.example .env
#   required: PALLISADE_DATABASE_URL, PALLISADE_SESSION_SECRET,
#             PALLISADE_STORAGE_SIGNING_KEY, PALLISADE_ANTHROPIC_API_KEY,
#             PALLISADE_VOYAGE_API_KEY

# 3. Database
alembic upgrade head

# 4. Run (each in its own shell, with .env sourced)
uvicorn web.api.main:app --reload --port 8000     # API
python -m pallisade_worker                        # worker
cd web/ui && npm install && npm run dev           # UI on :3001
```

The UI dev server runs on port **3001** (3000 is commonly taken); the API CORS allow-list
already includes it.

## Tests

```bash
source .env            # settings validation needs the env present
pytest                 # full suite (DB-backed tests use testcontainers → needs Docker)
pytest tests/pallisade_research   # fast, DB-free unit tests
```

## Notes

- `Dockerfile` is inherited from the monorepo and its entrypoint is stale — the supported
  dev path is the four commands above, not `docker build`. Fixing the container image is a
  follow-up.
- Not financial, investment, or trading advice. For licensed professional use only.
