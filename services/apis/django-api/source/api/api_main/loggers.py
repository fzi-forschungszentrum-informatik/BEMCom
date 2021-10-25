import logging

from prometheus_client import Counter


class PrometheusHandler(logging.StreamHandler):
    """
    Count each log message as Prometheus counter metric.
    """

    def __new__(cls, *args, **kwargs):
        """
        Ensure singleton, i.e. that the metric is only created once.
        """
        if not hasattr(cls, "prom_log_message_counter"):
            cls.prom_log_message_counter = Counter(
                "bemcom_djangoapi_log_messages_received_total",
                "Total number of log messages emitted by the BEMCom Django-API "
                "service.",
                ["function", "levelname", "loggername"],
            )
        return object.__new__(cls)

    @classmethod
    def emit(cls, record):
        """
        Count log record in Prometheus metric.

        Parameters
        ----------
        record : logging.LogRecord
            The record to publish.
        """
        cls.prom_log_message_counter.labels(
            function=record.funcName,
            levelname=record.levelname,
            loggername=record.name,
        ).inc()


class StreamHandlerPlusIPs(logging.StreamHandler):
    """
    Like the normal StreamHandler, apart that it glues the IPs of the requests
    to the log messages.
    """

    def emit(self, record):
        """
        Append IP addresses to log message if available. This is likely only
        the case for the django.requests and django.server loggers.
        See: https://docs.djangoproject.com/en/3.2/topics/logging/#id3
        See also the documentation regarding the header flags:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For

        Parameters
        ----------
        record : logging.LogRecord
            The record to publish.
        """
        if hasattr(record, "request"):
            forwarded = record.request.META.get("FORWARDED")
            x_forwarded_for = record.request.META.get("HTTP_X_FORWARDED_FOR")
            if forwarded:
                record.msg += " (FORWARDED: %s)" % forwarded
            elif x_forwarded_for:
                record.msg += " (HTTP_X_FORWARDED_FOR: %s)" % x_forwarded_for
            else:
                remote_addr = record.request.META.get("REMOTE_ADDR")
                record.msg += " (REMOTE_ADDR: %s)" % remote_addr
        super().emit(record)
