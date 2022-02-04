"""
This files allows placing pytest fixtures that apply to all tests of
the django-api service.
"""
import pytest
from prometheus_client import REGISTRY


@pytest.fixture(autouse=True)
def clean_prom_registry_after_test():
    """
    This seems necessary as the prometheus client will else complain
    about duplicate metrics in the registry.
    """
    yield  # this is where the testing happens

    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
