import os
from pathlib import Path

import garth
from dotenv import load_dotenv

load_dotenv()

TOKEN_DIR = str(Path(__file__).resolve().parent.parent.parent / "tokens")


def login():
    """Authenticate with Garmin Connect. Resumes saved tokens if available."""
    try:
        garth.resume(TOKEN_DIR)
    except Exception:
        email = os.environ.get("GARMIN_EMAIL")
        password = os.environ.get("GARMIN_PASSWORD")
        if not email or not password:
            raise RuntimeError(
                "GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env"
            )
        garth.login(email, password)
        garth.save(TOKEN_DIR)


def get_display_name() -> str:
    try:
        profile = garth.connectapi("/userprofile-service/socialProfile")
        return profile.get("fullName") or profile.get("displayName", "Unknown")
    except Exception:
        return "Unknown"


def is_authenticated() -> bool:
    try:
        garth.connectapi("/userprofile-service/socialProfile")
        return True
    except Exception:
        return False
