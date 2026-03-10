import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_display_name, is_authenticated, login
from .garmin_client import get_activity, list_activities
from .mappers import map_activity

app = FastAPI(title="Garmin Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Simple rate limiter: track last Garmin API call time
_last_garmin_call = 0.0
_RATE_LIMIT_SECONDS = 2.0


def _rate_limit():
    global _last_garmin_call
    now = time.time()
    elapsed = now - _last_garmin_call
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_garmin_call = time.time()


@app.on_event("startup")
def startup():
    login()


@app.get("/status")
def status():
    return {
        "authenticated": is_authenticated(),
        "displayName": get_display_name(),
    }


@app.get("/activities")
def activities(
    limit: int = Query(default=5, ge=1, le=20),
    type: str | None = Query(default=None),
):
    _rate_limit()
    try:
        raw_activities = list_activities(limit=limit, activity_type=type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    mapped = []
    for raw in raw_activities:
        result = map_activity(raw)
        if result is not None:
            mapped.append(result)
    return mapped


@app.get("/activities/{activity_id}")
def activity_detail(activity_id: str):
    _rate_limit()
    try:
        raw = get_activity(activity_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    result = map_activity(raw)
    if result is None:
        raise HTTPException(status_code=404, detail="Unsupported activity type")
    return result
