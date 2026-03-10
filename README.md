# Garmin Server

Local API server that fetches activities from Garmin Connect for the health-tracker PWA.

## Setup

1. Install [uv](https://docs.astral.sh/uv/)
2. Copy `.env.example` to `.env` and add your Garmin credentials:
   ```
   GARMIN_EMAIL=your@email.com
   GARMIN_PASSWORD=your-password
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```

## Run

```bash
uv run uvicorn garmin_server.server:app --host 127.0.0.1 --port 8787
```

The server binds to localhost only — not accessible from the network.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Auth status + display name |
| GET | `/activities?limit=5&type=running` | Recent activities (limit 1-20) |
| GET | `/activities/{activityId}` | Single activity detail |

## Token caching

On first run, garth authenticates with your credentials and saves OAuth tokens to `tokens/`. Subsequent starts resume from cached tokens (~1 year lifespan). Delete `tokens/` to force re-authentication.
