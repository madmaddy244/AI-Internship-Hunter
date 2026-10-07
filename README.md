# AI Internship Hunter & Application Agent

A resume-aware internship workspace for discovering openings, comparing role requirements with candidate evidence, preparing application drafts, and tracking progress. The app uses NVIDIA Nemotron 3.5 Lightning through Nebius Token Factory when configured. It never submits an external application.

## What it does

- Extracts selectable text from a PDF and structures profile details without inventing missing facts. Review and edit all extracted details.
- Searches current listings through Tavily when `TAVILY_API_KEY` is configured.
- Offers an explicit Demo Mode with fictional sample roles clearly labeled as examples, never as current openings.
- Computes a reproducible fit score from skills, preferred role, education, location, and experience. A Nemotron explanation is added only after a real model response.
- Saves roles to a persistent application tracker, supports status/notes updates, and saves editable generated drafts.
- Provides a profile-aware assistant when Nebius is configured.
- Keeps every application action manual. The app does not submit forms, send email, or claim that an application was submitted.

## Architecture

```text
React + Vite workspace
        │ same-origin /api requests
        ▼
FastAPI service ─────────────── SQLite (anonymous browser-session data)
        │                                  │
        ├── Nebius Token Factory            └── profile, extracted resume text,
        │   NVIDIA Nemotron 3.5 Lightning       found roles, tracker, activity
        └── Tavily Search API (optional)
```

The backend lives in `backend/` and the React application lives in `artifacts/internship-hunter/`. API models are defined in `lib/api-spec/openapi.yaml`; the TypeScript client is generated from that contract.

## Requirements and local setup

Requirements: Python 3.12+, Node.js 24+, and pnpm.

1. Install Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. Set `NEBIUS_API_KEY` to enable Nemotron and optionally set `TAVILY_API_KEY` for live internship searches. Keep credentials in Replit Secrets or an untracked `.env`; never commit them.

3. Start FastAPI from the repository root:

   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080
   ```

4. In a second terminal, start the frontend:

   ```bash
   PORT=5173 BASE_PATH=/ API_PROXY_TARGET=http://127.0.0.1:8080 \
     pnpm --filter @workspace/internship-hunter run dev
   ```

   The Vite development server proxies `/api` to the local FastAPI service. In Replit, use the managed `artifacts/api-server: API Server` and `artifacts/internship-hunter: web` services instead.

5. Open **Explore roles**, enter a role and location, and enable **Demo Mode** to try the interface without provider credentials. Demo listings are fictional and carry no application links.

## Provider configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Server-side Nebius Token Factory credential | Not configured |
| `NEBIUS_BASE_URL` | OpenAI-compatible API base URL | `https://api.tokenfactory.nebius.com/v1/` |
| `NEBIUS_MODEL` | Model used for extraction, tool calls, explanations, drafts, and assistant replies | `nvidia/Nemotron-3_5-Lightning` |
| `NEBIUS_ENABLED` | Set to `false` to disable model calls | `true` |
| `TAVILY_API_KEY` | Optional live internship web search | Not configured |
| `TAVILY_ENABLED` | Set to `false` to disable live search | `true` |
| `INTERNSHIP_HUNTER_DATABASE_URL` | SQLite database URL (separate from any workspace-level `DATABASE_URL`) | `sqlite:///./internship_agent.db` |

The app starts without either provider key. In that state, profile editing, deterministic match factors, saved-role tracking, and Demo Mode remain available. Assistant and draft generation return a clear configuration error instead of made-up AI output. Live search requires Tavily; the app does not silently replace a failed live search with sample listings.

## Run checks

```bash
python -m pytest
pnpm --filter @workspace/api-spec run codegen
pnpm --filter @workspace/internship-hunter run typecheck
pnpm --filter @workspace/internship-hunter run build
```

## Privacy and security notes

- API credentials are server-side only and are never returned from `/api/status`.
- Each browser receives a random, HTTP-only, SameSite session cookie. Its hash is used to scope the anonymous profile, search results, activity, and tracker rows. There is no login, account recovery, or cross-device sync in this version.
- The original PDF bytes are not saved. Extracted resume text and the structured profile are saved in local SQLite so matching and writing can use them on later requests. SQLite is not encrypted at rest by this app.
- When a model feature is used, the relevant profile fields and/or extracted resume text are sent to Nebius Token Factory. When live search is used, the query is sent to Tavily. Do not upload information you are not comfortable sending to those providers.
- Search result application links are only included when the result URL appears to point to a careers page or recognized job board. Verify the original listing before applying.
- This prototype has no account authentication or production data-retention controls. Do not expose it as a multi-user production service without adding authentication, secure database operations, rate limits, and a data deletion workflow.

## Real-provider verification status

The workspace integration must not be described as satisfying an event's real Nemotron-call requirement until a real request is made using a valid Nebius credential. No real Nebius inference request has been confirmed in this checkout. After configuring the key, confirm `/api/status` reports `ai_configured: true`, upload a text-based PDF or use the assistant, and verify the returned operation reports `ai_used: true` and the expected model. A passing local test does not prove provider access.

## License

MIT. See [LICENSE](LICENSE).
