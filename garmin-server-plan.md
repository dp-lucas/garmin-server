# Garmin Connect Direct Import — Implementation Plan

## Context
The health-tracker PWA imports Garmin data via manual TCX file uploads (export from Garmin website → upload in app). This plan creates a seamless in-app experience: tap a button on the Cardio page, see recent Garmin activities, select one, and import it directly — no file handling.

Since the PWA runs in the browser and can't call Garmin's servers directly (CORS + credential security), we need a lightweight local Python API server as a bridge.

**Device scope**: Desktop (direct Garmin fetch) + iPhone (TCX import fallback). The local server is only reachable on desktop. Activities imported on desktop sync to iPhone via Supabase automatically.

## Architecture

```
┌─────────────────────┐     fetch()      ┌──────────────────────┐     garth      ┌─────────────────┐
│  PWA (CardioPage)   │ ──────────────── │  Local API Server    │ ────────────── │  Garmin Connect │
│  localhost:5173     │   localhost:8787  │  Python + FastAPI    │                │                 │
└─────────────────────┘                  └──────────────────────┘                └─────────────────┘
```

## Separate Project (security)
The API server lives in its own repo: `C:\Users\JBK\Documents\mcp-garmin-server\`
- **Credential isolation** from the health-tracker repo (deployed to Vercel/GitHub)
- **Local-only**, never pushed to a remote
- `.env` and `tokens/` gitignored

## Tech Stack
- **Python** — `garth` is the most mature/reliable Garmin Connect client (reverse-engineered OAuth session auth)
- **FastAPI** — lightweight HTTP server with automatic OpenAPI docs
- **uvicorn** — ASGI server to run FastAPI
- **uv** — Python package manager (already installed)
- **No official Garmin API exists** — `garth` handles the unofficial auth + token refresh

## Project Structure

```
mcp-garmin-server/
├── pyproject.toml
├── .env.example            # GARMIN_EMAIL=, GARMIN_PASSWORD=
├── .env                    # Actual credentials (gitignored)
├── .gitignore
├── src/
│   └── garmin_server/
│       ├── __init__.py
│       ├── server.py       # FastAPI app, endpoints, CORS config
│       ├── garmin_client.py # garth wrapper with error handling + retry
│       ├── auth.py         # Credential loading, token resume/save
│       └── mappers.py      # Garmin activity → CardioEntry mapping
└── tokens/                 # garth token cache (gitignored)
    └── .gitkeep
```

## API Endpoints

### `GET /activities?limit=5&type=running`
Returns recent Garmin activities as summaries.
```json
[
  {
    "activityId": "12345678",
    "name": "Morning Run",
    "type": "running",
    "date": "2026-03-09",
    "distanceKm": 5.23,
    "durationMinutes": 28.5,
    "avgHeartRate": 145,
    "maxHeartRate": 172,
    "paceMinPerKm": 5.45
  }
]
```

### `GET /activities/{activityId}`
Returns full activity details (same fields + splits, elevation, cadence).

### `GET /status`
Returns auth status: `{ "authenticated": true, "displayName": "John" }`

## Frontend Changes (in health-tracker repo)

Replace the file-based "Import Garmin (.tcx)" button with a "Fetch from Garmin" flow:

1. **"Fetch from Garmin" button** — shown only when local server is reachable
2. **Activity list modal/sheet** — shows last 5 activities from Garmin with type, distance, duration, date
3. **Tap to import** — user taps an activity, it gets written to Dexie with `source: 'garmin'`
4. **Duplicate detection** — reuse existing logic (date + type + distance + duration check)
5. **Loading/error states** — spinner while fetching, error if server is unreachable
6. **TCX import kept as fallback** — always visible, secondary style

### New files in health-tracker:
- `src/lib/garmin-api.ts` — fetch wrapper for the local API (`getActivities()`, `getServerStatus()`)
- `src/components/cardio/GarminImportSheet.tsx` — modal/bottom sheet showing fetched activities

### Modified files:
- `src/pages/CardioPage.tsx` — add Garmin fetch button + sheet trigger (lines 246-301)

## Data Mapping (Python `mappers.py`)

| Garmin API field | Output field | Transform |
|---|---|---|
| `startTimeLocal` | `date` | Extract YYYY-MM-DD |
| `activityType.typeKey` | `type` | Map via lookup (running/cycling/swimming/walking) |
| `distance` | `distanceKm` | meters ÷ 1000, round 2 |
| `duration` | `durationMinutes` | seconds ÷ 60, round 1 |
| computed | `paceMinPerKm` | duration / distance, round 2 |
| `averageHR` | `avgHeartRate` | Round to int |
| `maxHR` | `maxHeartRate` | Round to int |
| `activityName` | `name` | Pass through for display |

**Type map:**
- running / trail_running / treadmill_running → `running`
- cycling / road_biking / mountain_biking / indoor_cycling → `cycling`
- lap_swimming / open_water_swimming → `swimming`
- walking / hiking → `walking`
- All others → skipped

## Authentication
1. Credentials in `.env`: `GARMIN_EMAIL`, `GARMIN_PASSWORD` (no MFA)
2. Token caching: `garth.resume("./tokens")` on startup → fallback to login + `garth.save("./tokens")`
3. Tokens last ~1 year; no credentials exposed via API endpoints

## Security & Network
- Server binds to `127.0.0.1:8787` only (not `0.0.0.0`)
- CORS allows both `http://localhost:5173` (Vite dev) and the production Vercel URL
- No credential endpoints; `/status` returns display name only
- Separate project, never deployed
- **Mixed content (HTTPS→HTTP)**: The Vercel-hosted PWA is HTTPS, but the local server is HTTP. Chrome allows `fetch()` to `http://localhost` as a special case. If this causes issues, we can add a self-signed cert to the local server later.
- **Garmin account safety**: No auto-polling or background sync. Fetches only happen on explicit user action. Rate-limit client to max 1 request per 2 seconds.

## Dependencies

**Python (`pyproject.toml`):**
- `fastapi>=0.115.0`
- `uvicorn>=0.34.0`
- `garth>=0.4.0`
- `python-dotenv>=1.0.0`

**No new npm dependencies** in health-tracker.

## Build Order

### Phase 1: Python API Server
1. Create `C:\Users\JBK\Documents\mcp-garmin-server\` with structure, `pyproject.toml`, `.gitignore`, `git init`
2. Implement `auth.py` — env loading, garth login/resume/save
3. Implement `garmin_client.py` — `list_activities(limit, activity_type)`, `get_activity(id)` with retry
4. Implement `mappers.py` — Garmin → CardioEntry-compatible JSON
5. Implement `server.py` — FastAPI app with 3 endpoints, CORS for localhost:5173, bind to 127.0.0.1:8787
6. Create `.env.example`
7. Test: `uv run uvicorn garmin_server.server:app` → `curl http://localhost:8787/activities?limit=3`

### Phase 2: Frontend Integration (in health-tracker)
8. Create `src/lib/garmin-api.ts` — typed fetch wrapper for local API, with `isServerAvailable()` check
9. Create `src/components/cardio/GarminImportSheet.tsx` — activity selection UI
10. Update `src/pages/CardioPage.tsx` — add Garmin fetch button (shown only when server is reachable), wire up sheet, handle import with existing duplicate detection. Keep TCX import always visible as fallback.

### Phase 3: Polish
11. Keep existing TCX import as fallback (move below Garmin fetch button, smaller/secondary style)
12. Add connection status indicator (green dot if server reachable)
13. Add `README.md` to mcp-garmin-server with setup instructions

## Existing Code to Reuse (health-tracker)
- `src/types/index.ts:28-42` — CardioEntry, CardioType, CardioSource interfaces
- `src/utils/records.ts` — `createRecord()` for generating new DB records
- `src/pages/CardioPage.tsx:263-274` — duplicate detection logic (same date/type/distance/duration)
- `src/pages/CardioPage.tsx:275-288` — pace calculation + Dexie insert pattern
- `src/lib/garmin.ts` — reference for field mapping conventions (meters→km, seconds→min)

## Verification
1. Start Python server: `cd mcp-garmin-server && uv run uvicorn garmin_server.server:app --host 127.0.0.1 --port 8787`
2. Verify `/status` returns authenticated
3. Verify `/activities?limit=5` returns recent activities
4. Start PWA: `npm run dev`
5. Navigate to Cardio page, tap "Fetch from Garmin"
6. Verify activity list appears with correct data
7. Select an activity, verify it imports to Dexie with `source: 'garmin'`
8. Select the same activity again, verify duplicate detection blocks it
9. Verify existing TCX file import still works as fallback

## Running the Server
```bash
cd C:\Users\JBK\Documents\mcp-garmin-server
uv run uvicorn garmin_server.server:app --host 127.0.0.1 --port 8787
```
