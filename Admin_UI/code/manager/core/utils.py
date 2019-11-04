from datetime import datetime, timezone

def datetime_from_timestamp(timestamp, tz_aware=True):
    """
    Convert timestamp to datetime object.

    Arguments:
    ----------
    timestamp: int
        Milliseconds since 1.1.1970 UTC
    tz_aware: bool
        If true make datetime object timezone aware, i.e. in UTC.

    Returns:
    --------
    dt: datetime object
        Corresponding datetime object
    """
    dt = datetime.fromtimestamp(timestamp / 1000.)
    if tz_aware:
        dt = dt.astimezone(timezone.utc)
    return dt
