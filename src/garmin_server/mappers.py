TYPE_MAP = {
    "running": "running",
    "trail_running": "running",
    "treadmill_running": "running",
    "cycling": "cycling",
    "road_biking": "cycling",
    "mountain_biking": "cycling",
    "indoor_cycling": "cycling",
    "lap_swimming": "swimming",
    "open_water_swimming": "swimming",
    "walking": "walking",
    "hiking": "walking",
}


def map_activity(raw: dict) -> dict | None:
    """Map a raw Garmin activity to our API response format.

    Returns None if the activity type is not supported.
    """
    activity_type = raw.get("activityType", {})
    type_key = activity_type.get("typeKey", "")
    mapped_type = TYPE_MAP.get(type_key)
    if mapped_type is None:
        return None

    distance_m = raw.get("distance", 0) or 0
    duration_s = raw.get("duration", 0) or 0
    distance_km = round(distance_m / 1000, 2) if distance_m else None
    duration_min = round(duration_s / 60, 1) if duration_s else None

    pace = None
    if distance_km and duration_min:
        pace = round(duration_min / distance_km, 2)

    avg_hr = raw.get("averageHR")
    max_hr = raw.get("maxHR")

    # Extract date from startTimeLocal (format: "2026-03-09 07:30:00")
    start_time = raw.get("startTimeLocal", "")
    date = start_time[:10] if start_time else None

    return {
        "activityId": str(raw.get("activityId", "")),
        "name": raw.get("activityName", ""),
        "type": mapped_type,
        "date": date,
        "distanceKm": distance_km,
        "durationMinutes": duration_min,
        "avgHeartRate": round(avg_hr) if avg_hr else None,
        "maxHeartRate": round(max_hr) if max_hr else None,
        "paceMinPerKm": pace,
    }
