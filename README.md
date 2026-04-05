# chirandhAi

End-to-end flow for **ATS-oriented resume refinement**: paste a resume and job description, get structured edit proposals and a LaTeX draft, then **confirm** before a worker builds a **PDF** (Tectonic) and stores it in S3-compatible storage.

Repository: [github.com/chirandh/chirandhAi](https://github.com/chirandh/chirandhAi)

---

## Requirements

- **Docker** and **Docker Compose** (recommended), or
- **Python 3.11+** and **Node 20+** if you run the API/UI locally against Dockerized dependencies.

---

## Run UI and backend (Docker Compose)

From the repo root:

```bash
docker compose up --build
```

This starts **Postgres**, **Redis**, **MinIO**, the **FastAPI** app, the **ARQ worker** (PDF jobs), and the **web UI** (nginx + static React build).

| What | URL | Notes |
|------|-----|--------|
| **Web UI** | [http://localhost:3000](http://localhost:3000) | Nginx serves the SPA and proxies API routes to the backend (same origin). |
| **API** | [http://localhost:8000](http://localhost:8000) | Direct HTTP access; interactive docs at [/docs](http://localhost:8000/docs). |
| **MinIO API** | [http://localhost:9000](http://localhost:9000) | Object storage; presigned PDF links use `localhost:9000` so the browser can open them. |
| **MinIO console** | [http://localhost:9001](http://localhost:9001) | Login: `minio` / `minio123456` (from Compose). |

### API key for the UI

Compose sets a default key unless you override it:

- Default: **`docker-dev-key`**
- Override: set **`API_KEYS`** in your environment or a `.env` file next to `docker-compose.yml` before `docker compose up`.

In the UI, paste that value into the API key field (it is stored in **sessionStorage** in the browser).

### OpenAI (optional)

LLM calls are stubbed if **`OPENAI_API_KEY`** is empty. To use real proposals and scores:

```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

Or add `OPENAI_API_KEY` to a `.env` file in the project root (Compose reads it for variable substitution).

---

## Local development (hot-reload UI)

Run the full backend stack in Docker, but the **React** app with Vite on your machine:

```bash
# Terminal 1 — API, worker, data stores (no `web` service)
docker compose up --build redis postgres minio api worker
```

```bash
# Terminal 2 — UI with proxy to localhost:8000
cd frontend
npm ci
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)**. Vite proxies `/sessions`, `/jobs`, `/artifacts`, `/health`, and `/ready` to the API on port **8000** (see [`frontend/vite.config.ts`](frontend/vite.config.ts)).

Use the same API key as the **`api`** container (**`docker-dev-key`** by default).

---

## Configuration reference

Copy [`.env.example`](.env.example) to `.env` and adjust as needed. Important variables:

| Variable | Purpose |
|----------|---------|
| `API_KEYS` | Comma-separated secrets; required header **`X-API-Key`** on API routes. |
| `DATABASE_URL` | Async SQLAlchemy URL (Postgres in Compose, SQLite possible for local experiments). |
| `REDIS_URL` | Redis for rate limits (non-test) and ARQ job queue. |
| `S3_ENDPOINT_URL` | **Inside Docker**, use `http://minio:9000` for uploads. |
| `S3_PRESIGN_ENDPOINT_URL` | **Browser-facing** host for presigned PDF URLs (e.g. `http://localhost:9000` in Compose). |
| `OPENAI_API_KEY` | Optional; enables real LLM proposals and ATS scoring. |

---

## Useful commands

```bash
# OpenAPI JSON (e.g. Custom GPT Actions)
python scripts/export_openapi.py > openapi.json

# Tests (from repo root, Python venv with dev deps)
pip install -r requirements.txt pytest pytest-asyncio httpx ruff
pytest
ruff check app tests scripts
```

---

## License

Add a license file if you want this repo to be clearly open source (e.g. MIT).
