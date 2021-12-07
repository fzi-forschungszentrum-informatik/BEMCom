"""
This is a configuration file for the gunicorn production server.

Currently, this only contains some code required by the Prometheus exporter.
"""
from prometheus_client import multiprocess

def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
