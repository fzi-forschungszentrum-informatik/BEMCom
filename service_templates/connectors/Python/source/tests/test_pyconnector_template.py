#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime

from unittest.mock import MagicMock

from .base import TestClassWithFixtures
from pyconnector_template.pyconector_template import SensorFlow


class FakeDatetime():
    pass

class TestSensorFlowRun(TestClassWithFixtures):

    fixture_names = ('caplog', )

    def setup_method(self, method):

        self.sf = SensorFlow()

        # Patch receive_raw_msg and add return value with realistic signature.
        self.raw_msg_return = {
            "payload": {
                "raw_message": '{"dp_1": 2.1, "dp_2": "ok"}',
            }
        }
        self.sf.receive_raw_msg = MagicMock(
            return_value=self.raw_msg_return
        )

        # There is no control flow after the check for raw message DB that
        # would depend on the content of the message. Just use these
        # to check if the mehtods are called.
        self.sf.parse_raw_msg = MagicMock()
        self.sf.flatten_parsed_msg = MagicMock()
        self.sf.update_available_datapoints = MagicMock()
        self.sf.filter_and_publish_datapoint_values = MagicMock()

        # Overload configuration that would be provided by the Connector.
        self.sf.mqtt_client = MagicMock()
        self.sf.SEND_RAW_MESSAGE_TO_DB = False
        self.sf.MQTT_TOPIC_RAW_MESSAGE_TO_DB = "tpyco/raw_message_to_db"

    def test_receive_raw_msg_is_called(self):
        """
        This function is an essential part of the run logic.
        """
        self.sf.run_sensor_flow()
        self.sf.receive_raw_msg.assert_called()

    def test_timestamp_in_message(self):
        """
        Value messages must contain timestemps (see BEMCom message format).
        """
        self.sf.run_sensor_flow()

        msg = self.sf.parse_raw_msg.call_args.kwargs["raw_msg"]

        assert "timestamp" in msg["payload"]

    def test_timestamp_correct_value(self):
        """
        Verify that the timestamp of the message is correctly now in UTC.

        For that sake we comute the correct timestamp at beginning of the test
        and expect that the computed value is the range between this value
        and 10 seconds later, which should be realistic even on VERY slow
        machines.
        """
        expected_ts = round(datetime.timestamp(datetime.utcnow()) * 1000)

        self.sf.run_sensor_flow()

        msg = self.sf.parse_raw_msg.call_args.kwargs["raw_msg"]
        actual_ts = msg["payload"]["timestamp"]

        assert actual_ts >= expected_ts
        assert actual_ts < expected_ts + 10000

    def test_no_send_raw_msg_to_db_on_false(self):
        """
        Validate that no raw message is sent to the raw message DB if this
        option is deactivated via setting flag.
        """
        self.sf.SEND_RAW_MESSAGE_TO_DB = False

        self.sf.run_sensor_flow()

        # publish should only been called once, i.e. for sending
        # final message.
        assert self.sf.mqtt_client.publish.call_count == 0

    def test_send_raw_msg_to_db(self):
        """
        Check that the raw message is sent to raw message db if this option
        is set.
        """
        self.sf.SEND_RAW_MESSAGE_TO_DB = True

        self.sf.run_sensor_flow()

        expected_raw_msg = self.raw_msg_return["payload"]["raw_message"]
        expected_topic = self.sf.MQTT_TOPIC_RAW_MESSAGE_TO_DB
        # Ensure the message is received by the raw message DB.
        expected_qos = 2

        publish_call = self.sf.mqtt_client.publish.call_args_list[0]
        actual_topic = publish_call.kwargs["topic"]
        actual_payload = json.loads(publish_call.kwargs["payload"])
        actual_raw_msg = actual_payload["raw_message"]
        actual_qos = publish_call.kwargs["qos"]

        assert expected_raw_msg == actual_raw_msg
        assert expected_topic == actual_topic
        assert expected_qos == actual_qos

    def test_send_raw_msg_to_db_bytes(self):
        """
        Check that the raw message is sent to raw message db if this option
        is set. Here check special handling if raw message is in bytes,
        as bytes cannot be serialized to JSON.
        """
        self.sf.SEND_RAW_MESSAGE_TO_DB = True
        raw_msg_bytes_return = {
            "payload": {
                "raw_message": b'some bytes and stuff'
            }
        }
        self.sf.receive_raw_msg = MagicMock(
            return_value=raw_msg_bytes_return
        )

        self.sf.run_sensor_flow()

        expected_raw_msg = {
            "bytes": b'some bytes and stuff'.decode()
        }

        publish_call = self.sf.mqtt_client.publish.call_args_list[0]
        actual_payload = json.loads(publish_call.kwargs["payload"])
        actual_raw_msg = actual_payload["raw_message"]

        assert expected_raw_msg == actual_raw_msg

    def test_parse_raw_msg_called(self):
        """
        This function is an essential part of the run logic.
        """
        self.sf.run_sensor_flow()
        self.sf.parse_raw_msg.assert_called()

    def test_flatten_parsed_msg_called(self):
        """
        This function is an essential part of the run logic.
        """
        self.sf.run_sensor_flow()
        self.sf.flatten_parsed_msg.assert_called()

    def test_update_available_datapoints_called(self):
        """
        This function is an essential part of the run logic.
        """
        self.sf.run_sensor_flow()
        self.sf.update_available_datapoints.assert_called()

    def test_filter_and_publish_datapoint_values_called(self):
        """
        This function is an essential part of the run logic.
        """
        self.sf.run_sensor_flow()
        self.sf.filter_and_publish_datapoint_values.assert_called()