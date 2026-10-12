"""EC2 instance facts from IMDSv2 (the launch template sets hop limit 2 so containers can reach it)."""
import time
import urllib.error
import urllib.request

from . import config

IMDS = "http://169.254.169.254/latest"

_cached_token = None
_token_time = 0

def _token():
    global _cached_token, _token_time
    if _cached_token and time.time() - _token_time < 240:
        return _cached_token
    req = urllib.request.Request(
        f"{IMDS}/api/token", method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"})
    _cached_token = urllib.request.urlopen(req, timeout=1).read().decode()
    _token_time = time.time()
    return _cached_token

def _get(path):
    """Metadata value, or None off EC2 / when the path does not exist (404)."""
    try:
        req = urllib.request.Request(f"{IMDS}/meta-data/{path}", headers={"X-aws-ec2-metadata-token": _token()})
        return urllib.request.urlopen(req, timeout=1).read().decode()
    except (urllib.error.URLError, OSError):
        return None


def life_cycle():
    """'spot', 'on-demand' or 'unknown' (not on EC2)."""
    if config.INSTANCE_LIFECYCLE:
        return config.INSTANCE_LIFECYCLE
    return _get("instance-life-cycle") or "unknown"


def instance_id():
    if config.INSTANCE_LIFECYCLE:  # forced off EC2: skip the IMDS round trip
        return "local"
    return _get("instance-id") or "local"


def spot_interruption_pending():
    """True once EC2 has scheduled this Spot instance for interruption (2-minute notice)."""
    if config.INSTANCE_LIFECYCLE:
        return False
    return _get("spot/instance-action") is not None


# These act as module-level constants for the life of the container.
LIFE_CYCLE = life_cycle()
INSTANCE_ID = instance_id()
IS_SPOT = LIFE_CYCLE == "spot"
