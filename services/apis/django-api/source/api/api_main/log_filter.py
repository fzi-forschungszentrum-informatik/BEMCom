import logging


class IPAddressFilter(logging.Filter):
    """
    Allows to add IP addresses to certain log messages.

    See also:
    https://stackoverflow.com/a/69242328
    """

    def filter(self, record):
        if hasattr(record, "request"):
            x_forwarded_for = record.request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                record.ip = x_forwarded_for.split(",")[0]
            else:
                record.ip = record.request.META.get("REMOTE_ADDR")
        return True
