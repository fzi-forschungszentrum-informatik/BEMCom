import pytz
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


def datetime_iso_format(dt, hide_microsec=True):
    """
    :param dt: a DateTime object
    :param hide_microsec: If true, the microseconds are not displayed
    :return: Timestamp similar to ISO-format but nicer
    """
    if hide_microsec:
        dt = dt.replace(microsecond=0)
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=' ')
    return dt + " (UTC)"


def timestamp_utc_now():
    """
    Returns the timestamp of the current UTC time in milliseconds.
    Rounded to full microseconds.
    """
    return round(datetime.now(tz=timezone.utc).timestamp() * 1000)
