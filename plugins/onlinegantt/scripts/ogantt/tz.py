"""Timezone helpers.

The .gantt file stores every date as a UTC ISO string ("2026-10-04T05:00:00.000Z")
that represents a *local* working-hour instant (08:00 in Asia/Riyadh above), and
records the IANA zone name in advanced.timezone plus the JavaScript
getTimezoneOffset() value (minutes, sign inverted) in advanced.timezoneOffset.

zoneinfo is standard library on Python 3.9+, but the IANA database itself is
missing on most Windows installs.  We therefore accept an explicit utcOffset
("+03:00") in the plan spec and also carry a small built-in table for zones that
never observe DST, so the scripts stay dependency-free.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

try:  # pragma: no cover - depends on the host
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

# Fixed-offset zones (no daylight saving) that are safe to hard-code.
_FIXED = {
    "UTC": 0, "Etc/UTC": 0, "GMT": 0,
    "Asia/Riyadh": 180, "Asia/Kuwait": 180, "Asia/Bahrain": 180, "Asia/Qatar": 180, "Asia/Aden": 180,
    "Asia/Baghdad": 180, "Asia/Amman": 180, "Africa/Nairobi": 180, "Europe/Istanbul": 180, "Europe/Moscow": 180,
    "Asia/Dubai": 240, "Asia/Muscat": 240, "Asia/Baku": 240, "Asia/Tbilisi": 240,
    "Asia/Karachi": 300, "Asia/Tashkent": 300, "Asia/Kolkata": 330, "Asia/Calcutta": 330, "Asia/Kathmandu": 345,
    "Asia/Dhaka": 360, "Asia/Bangkok": 420, "Asia/Jakarta": 420, "Asia/Ho_Chi_Minh": 420,
    "Asia/Singapore": 480, "Asia/Kuala_Lumpur": 480, "Asia/Manila": 480, "Asia/Shanghai": 480, "Asia/Hong_Kong": 480,
    "Asia/Tokyo": 540, "Asia/Seoul": 540, "Australia/Brisbane": 600, "Australia/Perth": 480,
    "Africa/Lagos": 60, "Africa/Johannesburg": 120, "Africa/Khartoum": 120, "Africa/Tripoli": 120,
    "America/Phoenix": -420, "America/Bogota": -300, "America/Lima": -300, "America/Sao_Paulo": -180,
    "Pacific/Honolulu": -600,
}

_OFFSET_RE = re.compile(r"^([+-])(\d{1,2})(?::?(\d{2}))?$")


def parse_offset(text: str) -> int:
    """'+03:00' / '+0300' / '+3' -> minutes."""
    m = _OFFSET_RE.match(text.strip())
    if not m:
        raise ValueError(f"Invalid utcOffset {text!r}; use e.g. '+03:00'")
    sign = 1 if m.group(1) == "+" else -1
    return sign * (int(m.group(2)) * 60 + int(m.group(3) or 0))


class Zone:
    def __init__(self, name: str, utc_offset: str | None = None):
        self.name = name or "UTC"
        self._tz = None
        self._fixed_minutes = None
        if utc_offset:
            self._fixed_minutes = parse_offset(utc_offset)
        elif ZoneInfo is not None:
            try:
                self._tz = ZoneInfo(self.name)
            except Exception:
                self._tz = None
        if self._tz is None and self._fixed_minutes is None:
            if self.name in _FIXED:
                self._fixed_minutes = _FIXED[self.name]
            else:
                raise ValueError(
                    f"Timezone {self.name!r} is not available on this machine (no IANA database). "
                    "Add \"utcOffset\": \"+HH:MM\" to calendar in the plan spec (e.g. \"+03:00\" for Asia/Riyadh), "
                    "or ask the user whether to install the 'tzdata' package (pip install tzdata)."
                )

    # local naive -> aware UTC
    def to_utc(self, local: datetime) -> datetime:
        if self._tz is not None:
            return local.replace(tzinfo=self._tz).astimezone(timezone.utc)
        return (local - timedelta(minutes=self._fixed_minutes)).replace(tzinfo=timezone.utc)

    def to_local(self, utc: datetime) -> datetime:
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=timezone.utc)
        if self._tz is not None:
            return utc.astimezone(self._tz).replace(tzinfo=None)
        return (utc.astimezone(timezone.utc) + timedelta(minutes=self._fixed_minutes)).replace(tzinfo=None)

    def offset_minutes(self, local: datetime) -> int:
        """UTC offset in minutes at the given local time (+180 for Riyadh)."""
        if self._tz is not None:
            off = local.replace(tzinfo=self._tz).utcoffset()
            return int(off.total_seconds() // 60) if off else 0
        return int(self._fixed_minutes)

    def js_timezone_offset(self, local: datetime) -> int:
        """Value of JavaScript Date.getTimezoneOffset() (sign inverted): -180 for Riyadh."""
        return -self.offset_minutes(local)


def available(name: str) -> bool:
    """True when `name` can be resolved on this machine without an explicit utcOffset."""
    try:
        Zone(name)
        return True
    except ValueError:
        return False


def iso_z(utc: datetime) -> str:
    """Format like JavaScript toISOString(): 2026-10-04T05:00:00.000Z"""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    utc = utc.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def parse_iso(text: str) -> datetime:
    """Parse the ISO strings written by the site (always ...Z) or offsets."""
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
