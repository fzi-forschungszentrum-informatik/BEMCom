#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from unittest.mock import MagicMock

from .base import TestClassWithFixtures
from pyconnector_template.pyconector_template import SensorFlow, Connector


class TestSensorFlowRun(TestClassWithFixtures):

    fixture_names = []

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

class TestSensorFlowFlattenParsedMsg(TestClassWithFixtures):

    fixture_names = []

    def setup_method(self, method):

        self.sf = SensorFlow()

        self.parsed_msg = {
            "payload": {
                "parsed_message": {
                    "device_1": {
                        "sensor_1": "2.12",
                        "sensor_2": "3.12"
                    }
                },
                "timestamp": 1573680749000
            }
        }

        self.parsed_msg_deeper = {
            "payload": {
                "parsed_message": {
                    "device_1": {
                        "sensor_1": "2.12",
                        "sensor_2": "3.12"
                    },
                    "device_2": {
                        "0": {
                            "sensor_1": "ok"
                        }
                    }
                },
                "timestamp": 1573680749000
            }
        }

    def test_output_format_correct(self):
        """
        Verify that the output of the function is flattened as expected.
        """
        expected_msg = {
            "payload": {
                "flattened_message": {
                    "device_1__sensor_1": "2.12",
                    "device_1__sensor_2": "3.12"
                },
                "timestamp": self.parsed_msg["payload"]["timestamp"]
            }
        }

        actual_msg = self.sf.flatten_parsed_msg(parsed_msg=self.parsed_msg)

        assert actual_msg == expected_msg

    def test_output_format_deeper_correct(self):
        """
        Verify that the output of the function is flattened as expected, also
        for an input with varying depth and more then 2 layers.
        """
        expected_msg = {
            "payload": {
                "flattened_message": {
                    "device_1__sensor_1": "2.12",
                    "device_1__sensor_2": "3.12",
                    "device_2__0__sensor_1": "ok",
                },
                "timestamp": self.parsed_msg["payload"]["timestamp"]
            }
        }

        actual_msg = self.sf.flatten_parsed_msg(
            parsed_msg=self.parsed_msg_deeper
        )

        assert actual_msg == expected_msg


class TestConnectorValidateAndUpdateDatapointMap(TestClassWithFixtures):

    fixture_names = ('caplog', )

    def setup_method(self, method):

        self.cn = Connector()

        # This is the name of the logger used in pyconnector_template.py
        self.logger_name = "pyconnector template"

        # Overload some attributes for testing.
        self.cn.mqtt_client = MagicMock()


    def test_valid_datapoint_map_is_stored(self):
        """
        Verify that valid datapoint_map objects are stored as expected.
        """
        datapoint_map = {
            "sensor": {
                "Channel__P__value__0": "example-connector/msgs/0001",
                "Channel__P__unit__0": "example-connector/msgs/0002",
            },
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
            }
        }

        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map)
        )

        assert self.cn.datapoint_map == datapoint_map

    def test_datapoint_map_with_missing_sensor_key_fails(self):
        """
        A datapoint_object must have a "sensor" entry by convention.
        """
        # Set up a new and empty logger for the test
        self.caplog.set_level(logging.DEBUG, logger=self.logger_name)
        self.caplog.clear()

        datapoint_map = {
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
            }
        }

        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map)
        )

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == 'ERROR'
        assert "No sensor key" in records[0].message

    def test_datapoint_map_with_missing_actuator_key_fails(self):
        """
        A datapoint_object must have a "actuator" entry by convention.
        """
        # Set up a new and empty logger for the test
        self.caplog.set_level(logging.DEBUG, logger=self.logger_name)
        self.caplog.clear()

        datapoint_map = {
            "sensor": {
                "Channel__P__value__0": "example-connector/msgs/0001",
                "Channel__P__unit__0": "example-connector/msgs/0002",
            },
        }

        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map)
        )

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == 'ERROR'
        assert "No actuator key" in records[0].message

    def test_datapoint_map_with_missing_sensor_dict_fails(self):
        """
        A datapoint_object must have a dict value under sensor entry by
        convention.
        """
        # Set up a new and empty logger for the test
        self.caplog.set_level(logging.DEBUG, logger=self.logger_name)
        self.caplog.clear()

        datapoint_map = {
            "sensor": None,
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
            }
        }

        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map)
        )

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == 'ERROR'
        assert "Sensor entry in datapoint_map" in records[0].message

    def test_datapoint_map_with_missing_actuator_dict_fails(self):
        """
        A datapoint_object must have a dict value under actuator entry by
        convention.
        """
        # Set up a new and empty logger for the test
        self.caplog.set_level(logging.DEBUG, logger=self.logger_name)
        self.caplog.clear()

        datapoint_map = {
            "sensor": {
                "Channel__P__value__0": "example-connector/msgs/0001",
                "Channel__P__unit__0": "example-connector/msgs/0002",
            },
            "actuator": None,
        }

        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map)
        )

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == 'ERROR'
        assert "Actuator entry in datapoint_map" in records[0].message

    def test_new_actuator_entry_triggers_subscribe(self):
        """
        A new entry in actuator part of the datapoint_map should trigger
        a subscribe action as the connector should subscribe to the topic
        of the newly selected datapoint.
        """
        # Assume this map has been set up before.
        datapoint_map_old ={
            "sensor": {},
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
            }
        }
        self.cn.datapoint_map = datapoint_map_old

        datapoint_map_update = {
            "sensor": {},
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
                "example-connector/msgs/0004": "Channel__T__setpoint__0",
            }
        }
        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map_update)
        )

        expceted_call_count = 1
        actual_call_count = self.cn.mqtt_client.subscribe.call_count
        assert actual_call_count == expceted_call_count

        expected_topic = "example-connector/msgs/0004"
        actual_topic = self.cn.mqtt_client.subscribe.call_args.kwargs["topic"]
        assert actual_topic == expected_topic

        # Also check that the subscribe is requested with maximum QOS request
        # to prevent message losses for actuator setpoints.
        expected_qos = 2
        actual_qos = self.cn.mqtt_client.subscribe.call_args.kwargs["qos"]
        assert actual_qos == expected_qos

    def test_removed_actuator_entry_triggers_unsubscribe(self):
        """
        A removed entry in actuator part of the datapoint_map should trigger
        an unsubscribe action as the connector should no longer receive
        messages for that actuator.
        """
        # Assume this map has been set up before.
        datapoint_map_old ={
            "sensor": {},
            "actuator": {
                "example-connector/msgs/0003": "Channel__P__setpoint__0",
                "example-connector/msgs/0004": "Channel__T__setpoint__0",
            }
        }
        self.cn.datapoint_map = datapoint_map_old

        datapoint_map_update = {
            "sensor": {},
            "actuator": {
                "example-connector/msgs/0004": "Channel__T__setpoint__0",
            }
        }
        self.cn.validate_and_update_datapoint_map(
            datapoint_map_json=json.dumps(datapoint_map_update)
        )

        expceted_call_count = 1
        actual_call_count = self.cn.mqtt_client.unsubscribe.call_count
        assert actual_call_count == expceted_call_count

        expected_topic = "example-connector/msgs/0003"
        actual_topic = self.cn.mqtt_client.unsubscribe.call_args.kwargs["topic"]
        assert actual_topic == expected_topic

class TestConnectorUpdateAvailableDatapoints(TestClassWithFixtures):

    fixture_names = []

    def setup_method(self, method):

        self.cn = Connector()

        # Overload some attributes for testing.
        self.cn.mqtt_client = MagicMock()
        self.cn.MQTT_TOPIC_AVAILABLE_DATAPOINTS = "tpyco/available_datapoints"


    def test_update_without_new_keys_publishes_not(self):
        """
        Updateing available_datapoints without new datapoint keys should
        not trigger sending an update via MQTT.
        """
        self.cn.available_datapoints = {
            "sensor": {
                "Channel__P__value__0": 0.122,
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": 0.4,
            }
        }

        available_datapoints_update = {
            "sensor": {
                "Channel__P__value__0": 9.222,
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": 6.4,
            }
        }
        self.cn.update_available_datapoints(
            available_datapoints=available_datapoints_update
        )

        expected_call_count = 0
        actual_call_count = self.cn.mqtt_client.publish.call_count
        assert actual_call_count == expected_call_count

    def test_update_without_new_keys_updates_example_values(self):
        """
        Updateing available_datapoints without new datapoint keys should
        update the example values so more recent values are published with
        the next new datapoint.
        """
        self.cn.available_datapoints = {
            "sensor": {
                "Channel__P__value__0": 0.122,
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": 0.4,
            }
        }

        available_datapoints_update = {
            "sensor": {
                "Channel__P__value__0": 9.222,
            },
            "actuator": {
                "Channel__P__setpoint__0": 6.4,
            }
        }
        self.cn.update_available_datapoints(
            available_datapoints=available_datapoints_update
        )

        expected_available_datapoints = {
                "sensor": {
                    "Channel__P__value__0": 9.222,
                    "Channel__P__unit__0": "kW",
                },
                "actuator": {
                    "Channel__P__setpoint__0": 6.4,
                }
            }
        actual_available_datapoints = self.cn.available_datapoints
        assert actual_available_datapoints == expected_available_datapoints

    def test_update_with_new_key_triggers_publish(self):
        """
        A new key should trigger publishing the latest available_datapoints
        dict.
        """
        for dp_type in ["sensor", "actuator"]:

            self.cn.available_datapoints = {
                "sensor": {
                    "Channel__P__value__0": 0.122,
                    "Channel__P__unit__0": "kW",
                },
                "actuator": {
                    "Channel__P__setpoint__0": 0.4,
                }
            }

            available_datapoints_update = {
                "sensor": {},
                "actuator": {}
            }
            available_datapoints_update[dp_type]["Channel__Q__sp__0"] = 6.4
            self.cn.update_available_datapoints(
                available_datapoints=available_datapoints_update
            )

            # Verify that the updated dict is stored.
            expected_available_datapoints = {
                "sensor": {
                    "Channel__P__value__0": 0.122,
                    "Channel__P__unit__0": "kW",
                },
                "actuator": {
                    "Channel__P__setpoint__0": 0.4,
                }
            }
            expected_available_datapoints[dp_type]["Channel__Q__sp__0"] = 6.4
            actual_available_datapoints = self.cn.available_datapoints
            assert actual_available_datapoints == expected_available_datapoints

            # Check that it is also published on the correct topic.
            mqtt_client = self.cn.mqtt_client
            expected_payload = json.dumps(expected_available_datapoints)
            actual_payload = mqtt_client.publish.call_args.kwargs["payload"]
            assert actual_payload == expected_payload

            expected_topic = self.cn.MQTT_TOPIC_AVAILABLE_DATAPOINTS
            actual_topic = mqtt_client.publish.call_args.kwargs["topic"]
            assert actual_topic == expected_topic