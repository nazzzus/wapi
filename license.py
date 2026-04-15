# license.py
"""
License activation and validation for WAPI.
Communicates with the backend API (or directly with Lemon Squeezy).
"""
from __future__ import annotations
import json
import uuid
import hashlib
import platform
import socket
from pathlib import Path

# Try requests; fall back gracefully if offline
try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# ── Config ──────────────────────────────────────────────────────────────────
# Change this to your deployed Railway URL before building the .exe
BACKEND_URL = "https://wapi-production-04e6.up.railway.app"

LICENSE_FILE = Path(__file__).parent / "wapi_license.json"
APP_VERSION  = "1.0.0"
TIMEOUT      = 8  # seconds


# ── Machine fingerprint ────────────────────────────────────────────────────

def get_instance_id() -> str:
    """Return a stable machine-specific ID (not user-identifiable)."""
    raw = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_machine_name() -> str:
    """Return a human-readable machine name."""
    try:
        return socket.gethostname()
    except Exception:
        return platform.node() or "Unknown"


# ── Local license cache ────────────────────────────────────────────────────

def load_cached_license() -> dict | None:
    """Load license data from local file."""
    try:
        if LICENSE_FILE.exists():
            return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def save_license_cache(data: dict) -> None:
    """Save license data to local file."""
    try:
        LICENSE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_license_cache() -> None:
    """Remove cached license (for deactivation/reset)."""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
    except Exception:
        pass


# ── API calls ──────────────────────────────────────────────────────────────

def activate_license(license_key: str) -> tuple[bool, str, dict]:
    """
    Activate a license key against the backend.
    Returns (success, message, data_dict).
    """
    if not _HAS_REQUESTS:
        return False, "Netzwerkfehler: requests nicht verfügbar", {}

    try:
        resp = _requests.post(
            f"{BACKEND_URL}/api/activate",
            json={
                "license_key":  license_key,
                "instance_id":  get_instance_id(),
                "machine_name": get_machine_name(),
                "app_version":  APP_VERSION,
            },
            timeout=TIMEOUT,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("valid"):
            cache = {
                "license_key":    license_key,
                "customer_name":  data.get("customer_name", ""),
                "customer_email": data.get("customer_email", ""),
                "plan":           data.get("plan", "standard"),
                "instance_id":    get_instance_id(),
            }
            save_license_cache(cache)
            return True, f"Lizenz aktiviert! Willkommen, {data.get('customer_name', '')}.", cache
        else:
            return False, data.get("error", "Ungültiger Lizenzschlüssel"), {}

    except _requests.exceptions.ConnectionError:
        return False, "Keine Verbindung zum Server. Bitte Internetverbindung prüfen.", {}
    except _requests.exceptions.Timeout:
        return False, "Server antwortet nicht (Timeout). Bitte später erneut versuchen.", {}
    except Exception as e:
        return False, f"Fehler bei der Aktivierung: {e}", {}


def validate_license_online(license_key: str) -> bool:
    """
    Quick online check — returns True if license is still valid.
    Falls back to True if server unreachable (offline grace).
    """
    if not _HAS_REQUESTS:
        return True  # offline grace

    try:
        resp = _requests.post(
            f"{BACKEND_URL}/api/validate",
            json={
                "license_key": license_key,
                "instance_id": get_instance_id(),
            },
            timeout=TIMEOUT,
        )
        data = resp.json()
        return data.get("valid", False)
    except Exception:
        return True  # offline grace — don't block user if server unreachable


def is_licensed() -> bool:
    """
    Check if this machine has a valid license.
    Uses cached data; does a quick online check every ~7 days.
    """
    cache = load_cached_license()
    if not cache or not cache.get("license_key"):
        return False

    # Periodic online validation (every 7 days via last_validated timestamp)
    import time
    last_check = cache.get("last_validated", 0)
    if time.time() - last_check > 7 * 24 * 3600:
        valid = validate_license_online(cache["license_key"])
        if not valid:
            clear_license_cache()
            return False
        cache["last_validated"] = time.time()
        save_license_cache(cache)

    return True


def get_license_info() -> dict:
    """Return cached license info dict (or empty dict if unlicensed)."""
    return load_cached_license() or {}
