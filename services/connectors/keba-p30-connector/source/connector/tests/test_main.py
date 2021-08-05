#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place tests for the connector specific methods here.
"""
import os
import json
import unittest
from unittest.mock import MagicMock
import threading

import pytest

from ..main import Connector, __version__


class TestReceiveRawMsg(unittest.TestCase):
    pass


class TestParseRawMsg(unittest.TestCase):
    pass


class TestSendCommand(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.charge_stations = {
            "test_1": "localhost",
            "test_2": "127.0.0.1",
        }
        os.environ["KEBA_P30_CHARGE_STATIONS"] = json.dumps(cls.charge_stations)

        # This is required to ensure the connector class can be created:
        os.environ["POLL_SECONDS"] = "10"
        os.environ["MQTT_BROKER_HOST"] = "locahost"
        os.environ["MQTT_BROKER_PORT"] = "1883"

    def test_valid_commands_are_send(self):
        """
        Verify that valid value messages addressing implemented datapoints
        are send on socket.
        """
        # All these message should be valid.
        test_value_msgs = [
            # datapoint_key, datapoint_value
            ["test_1__ena", "1"],
            ["test_1__curr", "36000"],
            ["test_1__setenergy", "100000"],
            ["test_1__display", "0 0 0 0 Test$Msg"],
        ]

        cn = Connector(version=__version__)
        for datapoint_key, datapoint_value in test_value_msgs:
            cn.keba_socket = MagicMock()
            cn.send_command(
                datapoint_key=datapoint_key, datapoint_value=datapoint_value
            )

            keba_command = datapoint_key.split("__")[-1]
            expected_send_to_args = (
                (keba_command + " " + datapoint_value).encode(),
                (self.charge_stations["test_1"], 7090)
            )
            assert cn.keba_socket.sendto.called
            actual_send_to_args = cn.keba_socket.sendto.mock_calls[-1].args
            assert actual_send_to_args == expected_send_to_args


class TestInit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.charge_stations = {
            "test_1": "localhost",
            "test_2": "127.0.0.1",
        }
        os.environ["KEBA_P30_CHARGE_STATIONS"] = json.dumps(cls.charge_stations)

        # This is required to ensure the connector class can be created:
        os.environ["POLL_SECONDS"] = "10"
        os.environ["MQTT_BROKER_HOST"] = "locahost"
        os.environ["MQTT_BROKER_PORT"] = "1883"

    def test_locks_created(self):
        """
        We require one lock per configured charge station. Check that these
        are created as expected.
        """
        cn = Connector(version=__version__)
        for expceted_charge_station_name in self.charge_stations:
            assert expceted_charge_station_name in cn.keba_p30_locks
            actual_lock = cn.keba_p30_locks[expceted_charge_station_name]
            assert isinstance(actual_lock, type(threading.Lock()))

    def test_actuator_datapoints_included(self):
        """
        Verifies that the compute_actuator_datapoints method is called and the
        result is used by the connector.
        """
        expected_available_datapoints = {
            "sensor": {},
            "actuator": {"test": "0"},
        }
        # This MagicMock applies for the unintialized class and affects
        # all subsequent tests too. We must undo it afterwards.
        cad_backup = Connector.compute_actuator_datapoints
        Connector.compute_actuator_datapoints = MagicMock(
            return_value=expected_available_datapoints["actuator"]
        )

        cn = Connector(version=__version__)
        actual_available_datapoints = cn._initial_available_datapoints
        Connector.compute_actuator_datapoints = cad_backup
        assert actual_available_datapoints == expected_available_datapoints


class TestComputeActuatorDatapoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.charge_stations = {
            "test_1": "localhost",
            "test_2": "127.0.0.1",
        }
        os.environ["KEBA_P30_CHARGE_STATIONS"] = json.dumps(cls.charge_stations)

        # This is required to ensure the connector class can be created:
        os.environ["POLL_SECONDS"] = "10"

    def test_actuator_datapoints_content_as_expected(self):
        """
        Verify that the expected values for the key_in_connector and
        example_value fields are returned.
        """
        cn = Connector(version=__version__)
        expected_actuator_datapoints = {
            "test_1__ena": "0",
            "test_1__curr": "63000",
            "test_1__setenergy": "100000",
            "test_1__display": "0 0 0 0 Hello$KEBA",
            "test_2__ena": "0",
            "test_2__curr": "63000",
            "test_2__setenergy": "100000",
            "test_2__display": "0 0 0 0 Hello$KEBA",
        }
        actual_actuator_datapoints = cn.compute_actuator_datapoints(
            self.charge_stations
        )
        assert actual_actuator_datapoints == expected_actuator_datapoints
