"""IP -> approximate location, for the admin analytics map. Uses a local
GeoLite2-City database (downloaded at image build time, see Dockerfile) —
no third-party API calls, no telemetry. Private/loopback/link-local IPs
(LAN, Tailscale, Docker-internal) correctly resolve to nothing, same as
any self-hosted geolocation tool: there's no meaningful "location" for a
connection that never left the local network."""

import ipaddress
import logging
from pathlib import Path

import geoip2.database
import geoip2.errors

logger = logging.getLogger("mradio.geoip")

_MMDB_PATH = Path(__file__).resolve().parent.parent / "GeoLite2-City.mmdb"

# Tailscale's CGNAT range (RFC 6598 "Shared Address Space") — Python's
# ipaddress module does NOT flag 100.64.0.0/10 as private/reserved, so
# without this it would fall through to a real GeoLite2 lookup. That
# lookup happens to return nothing today (the range has no meaningful
# public geolocation), but relying on "the database happens to have no
# entry" instead of an explicit check is fragile — and this app is
# reached over Tailscale (see KB.md), so this range is a realistic
# source of connections, not a hypothetical.
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")

_reader: geoip2.database.Reader | None = None
_reader_load_attempted = False


def _get_reader() -> geoip2.database.Reader | None:
    global _reader, _reader_load_attempted
    if _reader is not None or _reader_load_attempted:
        return _reader
    _reader_load_attempted = True
    try:
        _reader = geoip2.database.Reader(str(_MMDB_PATH))
    except OSError:
        logger.warning("GeoLite2-City.mmdb not found at %s — location lookups disabled", _MMDB_PATH)
    return _reader


def lookup(ip: str | None) -> dict | None:
    """Returns {country, country_code, city, lat, lon} or None if the IP
    is private/unresolvable/missing from the database."""
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        return None
    if addr in _TAILSCALE_CGNAT:
        return None
    reader = _get_reader()
    if reader is None:
        return None
    try:
        result = reader.city(ip)
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return None
    if result.location.latitude is None or result.location.longitude is None:
        return None
    return {
        "country": result.country.name or "",
        "country_code": result.country.iso_code or "",
        "city": result.city.name or "",
        "lat": result.location.latitude,
        "lon": result.location.longitude,
    }
