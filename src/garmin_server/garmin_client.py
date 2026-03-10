import garth

from .auth import login


def _request(endpoint: str, **kwargs):
    """Make a Garmin API request, retrying once on auth failure."""
    try:
        return garth.connectapi(endpoint, **kwargs)
    except Exception:
        login()
        return garth.connectapi(endpoint, **kwargs)


def list_activities(limit: int = 5, activity_type: str | None = None) -> list[dict]:
    """Fetch recent activities from Garmin Connect."""
    params = {"start": 0, "limit": limit}
    if activity_type:
        params["activityType"] = activity_type
    return _request(
        "/activitylist-service/activities/search", params=params
    )


def get_activity(activity_id: str) -> dict:
    """Fetch a single activity by ID."""
    return _request(f"/activity-service/activity/{activity_id}")
