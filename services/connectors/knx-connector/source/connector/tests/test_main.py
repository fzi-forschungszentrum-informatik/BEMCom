#!/usr/bin/env python3
"""
Place tests for the connector specific methods here.
"""
import os
from datetime import datetime
import unittest

from xknx.dpt import DPTBinary
from xknx.telegram import (
    GroupAddress,
    IndividualAddress,
    Telegram,
    TelegramDirection,
)
from xknx.telegram.apci import GroupValueWrite

from connector.main import Connector, __version__


async def run_knx_connection(self):
    """
    Do nothing to prevent an connection attempt.
    """
    pass


class TestReceiveRawMsg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These must be present to prevent errors.
        os.environ["KNX_GATEWAY_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        Connector.run_knx_connection = run_knx_connection

    def test_telegram_converted_to_dict(self):
        """
        Check that an arbitrary telegram is converted to the expected
        dict structure.
        """
        connector = Connector(version=__version__)
        telegram_as_object = Telegram(
            destination_address=GroupAddress("8/3/0"),
            direction=TelegramDirection.INCOMING,
            payload=GroupValueWrite(DPTBinary(1)),
            source_address=IndividualAddress("1.1.30"),
        )
        # Fix the timestamp to allow us to test against.
        telegram_as_object.timestamp = datetime(2022, 5, 31, 20, 34, 41, 262847)

        expected_telegram_as_dict = {
            "destination_address": "8/3/0",
            "direction": "Incoming",
            "payload_value_value": 1,
            "source_address": "1.1.30",
            "timestamp": "2022-05-31T20:34:41.262847",
        }

        actual_msg = connector.receive_raw_msg(raw_data=telegram_as_object)
        actual_telegram_as_dict = actual_msg["payload"]["raw_message"]

        assert actual_telegram_as_dict == expected_telegram_as_dict


class TestParseRawMsg(unittest.TestCase):
    def setUp(self):
        # These must be present to prevent errors.
        os.environ["KNX_GATEWAY_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["KNX_DATAPOINTS"] = ""
        Connector.run_knx_connection = run_knx_connection

    def test_telegram_dict_to_nested_dict(self):
        """
        Only group addresses are relevant, hence store only those.
        """
        knx_dps = '{"sensor": {"8/3/0": "DPT-1"}, "actuator": {}}'
        os.environ["KNX_DATAPOINTS"] = knx_dps
        connector = Connector(version=__version__)
        connector.knx_datapoints = {
            "sensor": {"8/3/0": "DPT-1"},
            "actuator": {},
        }
        test_msg = {
            "payload": {
                "raw_message": {
                    "destination_address": "8/3/0",
                    "direction": "Incoming",
                    "payload_value_value": 1,
                    "source_address": "1.1.30",
                    "timestamp": "2022-05-31T20:34:41.262847",
                },
                "timestamp": 1573680749000,
            }
        }

        actual_msg = connector.parse_raw_msg(raw_msg=test_msg)

        expected_msg = {
            "payload": {
                "parsed_message": {"8/3/0": True},
                "timestamp": 1573680749000,
            }
        }

        assert actual_msg == expected_msg

    def test_processing_stopped_for_not_knx_datapoints(self):
        """
        Don't process messages that are not listed in KNX_DATAPOINTS as we
        have no clue how to parse the values.
        """
        connector = Connector(version=__version__)
        test_msg = {
            "payload": {
                "raw_message": {
                    "destination_address": "8/3/0",
                    "direction": "Incoming",
                    "payload_value_value": 1,
                    "source_address": "1.1.30",
                    "timestamp": "2022-05-31T20:34:41.262847",
                },
                "timestamp": 1573680749000,
            }
        }

        actual_msg = connector.parse_raw_msg(raw_msg=test_msg)

        assert actual_msg is None


class TestSendCommand(unittest.TestCase):
    pass
