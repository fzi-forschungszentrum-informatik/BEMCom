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
        raw_msg_return = {
            "payload": {
                "raw_message": "Some raw bytes or somtehing"
            }
        }
        self.sf.receive_raw_msg = MagicMock(
            return_value=raw_msg_return
        )

        self.sf.mqtt_client = MagicMock()

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

        sent_payload = self.sf.mqtt_client.publish.call_args.kwargs["payload"]
        sent_payload = json.loads(sent_payload)

        assert "timestamp" in sent_payload

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

        sent_payload = self.sf.mqtt_client.publish.call_args.kwargs["payload"]
        sent_payload = json.loads(sent_payload)
        actual_ts = sent_payload["timestamp"]

        assert actual_ts >= expected_ts
        assert actual_ts < expected_ts + 10000

