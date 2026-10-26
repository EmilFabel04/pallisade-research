# Web: API and UI

The two web services for Pallisade Research. Setup, configuration and the full run order (database, API, worker, UI) are in the [root README](../README.md#running-it-locally).

| Service | What it is | Default port |
|---|---|---|
| `web/api` | FastAPI app (`web.api.main:app`): auth, research chat, debate runs and their SSE stream, documents, connections, watchlist, memo checks, PDF export | `8000` |
| `web/ui` | Next.js 15 App Router UI: Dashboard, Watchlist, Research, Debate, Artefacts, Settings | `3000` (next free port if taken) |

The UI's dev server rewrites `/api/*` to the API (`next.config.mjs`; override the target with `NEXT_PUBLIC_API_URL`), so the browser only talks to one origin.

Long-running work (document parsing and embedding, debates, memo checks) doesn't run in the API process. The API queues a job in Postgres and `python -m pallisade_worker` picks it up. Debate progress streams back through `GET /api/runs/{id}/stream`, which tails the run's event log and resumes from `Last-Event-ID`.

The API's extra Python dependencies (WeasyPrint, Jinja2, Markdown for PDF export) are in `web/api/requirements.txt`.
