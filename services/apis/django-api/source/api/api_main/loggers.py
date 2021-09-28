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
