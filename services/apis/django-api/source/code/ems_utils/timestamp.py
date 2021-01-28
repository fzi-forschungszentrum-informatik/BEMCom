"""
Utility functions for timestamps and datetime objects.
"""
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
        # Don't use astimezone here, as this will try add the hour delta
        # between the local timezone and UTC, while the timestamp is
        # alrady in UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def timestamp_utc_now():
    """
    Compute current timestamp.

    Returns:
    --------
    ts_utc_now : int
        The rounded timestamp of the current UTC time in milliseconds.
    """
    return round(datetime.now(tz=timezone.utc).timestamp() * 1000)


def datetime_to_pretty_str(dt):
    """
    Convert datetime object to string similar to ISO 8601 but more compact.

    Arguments:
    ----------
    dt: dateime object
        ... for which the string will be generated.

    Returns:
    --------
    dt_str: string
        The pretty string respresentation of the datetime object.
    """
    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt_str