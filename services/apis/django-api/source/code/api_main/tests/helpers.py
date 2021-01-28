#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Some generic code relevant for all tests.
"""

import unittest
import pytest

from api_main.models.datapoint import Datapoint
from api_main.models.connector import Connector


class TestClassWithFixtures(unittest.TestCase):
    """
    Allows the use of pytest fixtures as attributes in test classes.
    """

    fixture_names = ()

    @pytest.fixture(autouse=True)
    def auto_injector_fixture(self, request):
        names = self.fixture_names
        for name in names:
            setattr(self, name, request.getfixturevalue(name))


def connector_factory(connector_name=None):
    """
    Create a test connector in DB.

    This function is not thread save and may produce errors if other code
    inserts objects in models.Connector in parallel.

    Arguments:
    ----------
    connector_name: string or None
        If string uses this name as connector name. Else will automatically
        generate a name that is "test_connector_" + id of Connector. Be aware
        that mqtt topics are automatically generated from the name and that
        name and mqtt_topics must be unique.

    Returns:
    --------
    test_connector: Connector object
        A dummy Connector for tests.
    """
    if connector_name is None:
        next_id = Connector.objects.count() + 1
        connector_name = "test_connector_" + str(next_id)

    test_connector = Connector(
        name=connector_name,
    )
    test_connector.save()

    return test_connector


def datapoint_factory(connector, key_in_connector=None,
                      data_format="generic_text", type="sensor"):
    """
    Create a dummy datapoint in DB.

    This function is not thread save and may produce errors if other code
    inserts objects in Datapoint in parallel.

    Arguments:
    ----------
    connector: Connector object
        The connector the datapoint belongs to.
    key_in_connector:
        If string uses it's value as key_in_connector. Else will automatically
        generate a key that is "key__in__connector__" + id of Datapoint.
    data_format: str
        See Datapoint.
    type: str
        See Datapoint.

    Returns:
    --------
    test_datapoint: Datapoint object
        A dummy datapoint for tests.
    """
    if key_in_connector is None:
        next_id = Datapoint.objects.count() + 1
        key_in_connector = "key__in__connector__" + str(next_id)

    test_datapoint = Datapoint(
        connector=connector,
        key_in_connector=key_in_connector,
        data_format=data_format,
        type=type,
        is_active=True,
    )
    test_datapoint.save()

    return test_datapoint

