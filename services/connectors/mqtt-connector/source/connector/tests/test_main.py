#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place tests for the connector specific methods here.
"""
import os
import json
import unittest
from unittest.mock import MagicMock

import pytest

from ..main import Connector, __version__

# These are some useful default arguments for testing.
# Most importantly prevent the MQTT clients from connecting.
connector_default_kwargs = {
    "version": "0.0.1",
    "MqttClient": MagicMock(),
    "RemoteMqttClient": MagicMock(),
}


def apply_environ_defaults():
    """
    Apply sane default values for environment variables for the tests.
    """
    os.environ["MQTT_BROKER_PORT"] = "1883"
    os.environ["REMOTE_MQTT_BROKER_PORT"] = "1883"
    test_topic_mapping = {
        "sensor_topics": {"sensor/topic/1": {},},
        "actuator_topics": {"actuator/topic/1": {"example_value": "22.0"}},
    }
    os.environ["REMOTE_MQTT_BROKER_TOPIC_MAPPING"] = json.dumps(test_topic_mapping)


class TestReceiveRawMsg(unittest.TestCase):
    def setUp(self):
        apply_environ_defaults()

    def test_output_as_expected(self):
        """
        Verify that topic and payload are in the raw_msg object.
        """
        test_msg = MagicMock()
        test_msg.topic = "/test/"
        test_msg.payload = b'{"test": "value"}'

        expected_raw_msg = {
            "payload": {
                "raw_message": {"topic": "/test/", "payload": '{"test": "value"}',}
            }
        }

        cn = Connector(**connector_default_kwargs)
        actual_raw_msg = cn.receive_raw_msg(raw_data=test_msg)

        assert actual_raw_msg == expected_raw_msg


class TestParseRawMsg(unittest.TestCase):
    pass


class TestSendCommand(unittest.TestCase):
    pass


class TestParseTopicMapping(unittest.TestCase):
    def setUp(self):
        apply_environ_defaults()

    def test_valid_mapping_parsed_from_environ(self):
        """
        Verify that a valid mapping JSON on the environment variable returns
        the expected Python representation.
        """
        test_topic_mapping = {
            "sensor_topics": {
                "sensor/topic/1": {},
                "sensor/topic/with/single/+/wildcard": {},
                "sensor/topic/with/mulitlevel/wildcard/#": {},
            },
            "actuator_topics": {"actuator/topic/1": {"example_value": "22.0"}},
        }
        os.environ["REMOTE_MQTT_BROKER_TOPIC_MAPPING"] = json.dumps(test_topic_mapping)
        cn = Connector(**connector_default_kwargs)
        actual_topic_mapping = cn.parse_topic_mapping()

        assert actual_topic_mapping == test_topic_mapping

    def test_non_JSON_raises_exception(self):
        """
        We expect a topic mapping to be a valid JSON to be parsed.

        Here an empty string is not a valid JSON.
        """
        os.environ["REMOTE_MQTT_BROKER_TOPIC_MAPPING"] = ""
        with pytest.raises(ValueError):
            # This should already trigger the parsing.
            cn = Connector(**connector_default_kwargs)
            # This is just a fallback.
            _ = cn.parse_topic_mapping()

    def test_sensor_topics_not_in_topic_mapping_raises(self):
        """
        To prevent typos etc. we always expect this key.
        """
        test_topic_mapping = {"actuator_topics": {}}
        os.environ["REMOTE_MQTT_BROKER_TOPIC_MAPPING"] = json.dumps(test_topic_mapping)
        with pytest.raises(ValueError):
            # This should already trigger the parsing.
            cn = Connector(**connector_default_kwargs)
            # This is just a fallback.
            _ = cn.parse_topic_mapping()

    def test_actuator_topics_not_in_topic_mapping_raises(self):
        """
        To prevent typos etc. we always expect this key.
        """
        test_topic_mapping = {"sensor_topics": {}}
        os.environ["REMOTE_MQTT_BROKER_TOPIC_MAPPING"] = json.dumps(test_topic_mapping)
        with pytest.raises(ValueError):
            # This should already trigger the parsing.
            cn = Connector(**connector_default_kwargs)
            # This is just a fallback.
            _ = cn.parse_topic_mapping()


class TestComputeActuatorDatapoints(unittest.TestCase):
    def test_actuator_datapoints_matches_bemcom_format(self):
        """
        Verifies that the output of the compute_actuator_datapoints has the
        the expected content, i.e. that it matches the BEMCom message format.
        """
        test_topic_mapping = {
            "sensor_topics": {"sensor/topic/1": {},},
            "actuator_topics": {
                "actuator/topic/1": {"example_value": "22.0"},
                "actuator/topic/2": {"example_value": "26.0"},
            },
        }
        expected_actuator_datapoints = {
            "actuator/topic/1": "22.0",
            "actuator/topic/2": "26.0",
        }

        cn = Connector(**connector_default_kwargs)
        actual_actuator_datapoints = cn.compute_actuator_datapoints(
            topic_mapping=test_topic_mapping
        )

        assert actual_actuator_datapoints == expected_actuator_datapoints
