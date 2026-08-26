"""
SentinelRisk — Centralized Timezone & ISO-8601 UTC Standardization Utilities

Standards:
  1. Internal System Storage:
     - All system-generated timestamps (assessment uploads, case creations, audit logs,
       merchant alerts) MUST be generated and stored as timezone-aware UTC in ISO-8601 format:
       e.g., "YYYY-MM-DDTHH:MM:SSZ" (or sub-second ISO with 'Z' / '+00:00').
  2. Historical Dataset Event Timestamps:
     - Preserved exactly as provided in raw/benchmark datasets (no synthetic timezone shift).
  3. Presentation Layer:
     - System timestamps are converted to the user's browser/local timezone dynamically.
  4. Backward Compatibility:
     - Automatically normalizes legacy naive UTC strings (e.g. "2026-08-25 14:28:44") to standard ISO-8601 UTC.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union
import re


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Return current UTC timestamp in standard ISO-8601 UTC format:
    e.g., '2026-08-25T14:31:03Z'.
    """
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_and_standardize_utc(ts: Optional[Union[str, datetime]]) -> Optional[str]:
    """
    Safely parse any timestamp (naive UTC string, ISO string, datetime object)
    and standardize to standard ISO-8601 UTC format ('YYYY-MM-DDTHH:MM:SSZ').

    Handles:
      - '2026-08-25 14:28:44' (legacy naive UTC) -> '2026-08-25T14:28:44Z'
      - '2026-08-25T14:28:44Z' -> '2026-08-25T14:28:44Z'
      - '2026-08-25T14:28:44+00:00' -> '2026-08-25T14:28:44Z'
      - '2026-08-25T19:58:44+05:30' -> '2026-08-25T14:28:44Z'
      - datetime object (naive or aware) -> 'YYYY-MM-DDTHH:MM:SSZ'
    """
    if ts is None:
        return None

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            # Assume naive datetime is in UTC
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    ts_str = str(ts).strip()
    if not ts_str:
        return None

    # Handle standard naive space-separated format "YYYY-MM-DD HH:MM:SS"
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$", ts_str):
        clean_str = ts_str.split(".")[0].replace(" ", "T") + "Z"
        return clean_str

    # Handle "YYYY-MM-DDTHH:MM:SS" without Z
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", ts_str):
        return ts_str + "Z"

    # Try standard Python fromisoformat
    try:
        # Replace trailing 'Z' with '+00:00' for fromisoformat compatibility if needed
        iso_str = ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Fallback to returning original string if unparseable
        return ts_str


def format_utc_to_timezone(utc_iso_str: str, tz_name: str = "Asia/Kolkata") -> str:
    """
    Convert a standardized UTC ISO string to a human-readable local time string
    in the specified timezone (e.g. 'Asia/Kolkata', 'America/New_York', 'UTC').

    Example:
      format_utc_to_timezone('2026-08-25T14:28:44Z', 'Asia/Kolkata')
      -> '2026-08-25 19:58:44 IST'
    """
    std_utc = parse_and_standardize_utc(utc_iso_str)
    if not std_utc:
        return "--"

    try:
        # Parse standard UTC
        dt = datetime.strptime(std_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        target_tz = ZoneInfo(tz_name)
        local_dt = dt.astimezone(target_tz)
        tz_abbr = local_dt.strftime("%Z") or tz_name
        return local_dt.strftime(f"%Y-%m-%d %H:%M:%S {tz_abbr}").strip()
    except Exception:
        return std_utc
