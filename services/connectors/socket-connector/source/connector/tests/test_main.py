#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place tests for the connector specific methods here.
"""
import os
import json
import yaml
import socket
import unittest
from time import sleep
from unittest.mock import MagicMock
from threading import Thread

import pytest

from ..main import Connector, __version__


class RecursiveMagicMock(MagicMock):
    """
    Once initialized this mock just returns itself instead of new mock
    object. This allows you to test wether the init calls where correct.
    """

    def __call__(self, *args, **kwargs):
        # This is required that all mock calls are stored.
        _ = super().__call__(*args, **kwargs)
        return self


class TcpTestServer:
    """
    A simple context manager that allows starting a TCP server in a process.
    """

    def __enter__(self):
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        server_socket.bind(("localhost", 0))
        self.server_socket = server_socket
        used_port = server_socket.getsockname()[1]

        def send_data_and_close(server_socket):
            server_socket.listen()
            connection, client_address = server_socket.accept()
            connection.send("test message".encode())
            connection.close()

        self.thread = Thread(
            target=send_data_and_close,
            kwargs={"server_socket": server_socket},
            daemon=True,
        )
        self.thread.start()
        return used_port

    def __exit__(self, exception_type, exception_value, traceback):
        # Close the socket and stop thread after we are done
        #
        self.server_socket.close()
        # self.thread.join()


class TestSocketClient(unittest.TestCase):
    def setup_class(self):
        # Some generally useful kwargs for Connector to ensure that
        # run doesn't fail or blocks for ages.
        self.connector_default_kwargs = {
            "MqttClient": MagicMock,
            "heartbeat_interval": 0.05,
            "version": __version__,
        }

    def test_data_received_from_tcp(self):
        """
        Verify that we can receive data from TCP remote and that the
        raw data is forwarded as expected.

        BTW: This tests will always end with a error message like:
            ERROR    pyconnector:pyconector_template.py:726 Connector
                     main loop has caused an unexpected exception. Shuting down.
            This is the normal behaviour as
        """
        with TcpTestServer() as used_port:
            os.environ["SERVER_IP"] = "localhost"
            os.environ["SERVER_PORT"] = str(used_port)
            os.environ["MQTT_BROKER_HOST"] = "localhost"
            os.environ["MQTT_BROKER_PORT"] = "1883"

            # Creat a mock for the mqtt client that keeps the broker side
            # thread active for a bit, so it appears that the process is healthy.
            def fake_loop_forever():
                sleep(0.05)

            _MqttClient_mock = RecursiveMagicMock()
            _MqttClient_mock.loop_forever = fake_loop_forever

            cn = Connector(**self.connector_default_kwargs)
            cn.run_sensor_flow = MagicMock()
            cn._MqttClient = _MqttClient_mock
            cn.run()

            # This will fail if run_sensor_flow hasn't been called
            # as expected or the raw_data has not been forwarded to
            # run_sensor_flow
            expected_raw_data = "test message".encode()
            actual_raw_data = cn.run_sensor_flow.call_args.kwargs["raw_data"]
            assert actual_raw_data == expected_raw_data


class TestReceiveRawMsg(unittest.TestCase):
    """
    Not much to test here as the connection logic resides in the
    run_socket_client method which is tested in the class above ...
    """

    def test_output_format_correct(self):
        """
        ... hence just check that the output format is as expected.
        """
        test_raw_data = b'{"instantaneousActivePower":"10150","instantaneousCurrent1":"22.50","instantaneousCurrent2":"20.50000000000000150","instantaneousCurrent3":"20.0","instantaneousCurrentOBIS91":"19.00","instantaneousFrequency":"50.01","instantaneousManufacturerSpecificReactivePower":"8550","instantaneousPowerFactorAll":"0.76","instantaneousPowerFactorL1":"0.66","instantaneousPowerFactorL2":"0.72","instantaneousPowerFactorL3":"0.9","instantaneousVoltage1":"228.53","instantaneousVoltage2":"228.63","instantaneousVoltage3":"228.02","phaseAngleIL1_UL1":"301.0","phaseAngleIL2_UL1":"59.0","phaseAngleIL3_UL1":"202.0","phaseAngleUL1_UL1":"0.0","phaseAngleUL2_UL1":"120.0","phaseAngleUL3_UL1":"240.0"}\r\n'
        expected_msg = {"payload": {"raw_message": str(test_raw_data)}}
        cn = Connector(version=__version__)
        actual_msg = cn.receive_raw_msg(raw_data=test_raw_data)

        assert actual_msg == expected_msg


class TestParseRawMsg(unittest.TestCase):
    def test_json_parsed_correctly(self):
        os.environ["PARSE_AS"] = "JSON"
        cn = Connector(version=__version__)

        # A message that allows us to differtiate between encodings due to
        # non ASCII characters.
        test_msg_obj = {
            "dummy_dp": {"sensor_1": 2.0, "sensor_2": True, "sensor_3": "A string.",}
        }
        timestamp = 1618256642000

        test_raw_msg = {
            "payload": {
                "raw_message": str(json.dumps(test_msg_obj).encode()),
                "timestamp": timestamp,
            },
        }
        expected_parsed_msg = {
            "payload": {"parsed_message": test_msg_obj, "timestamp": timestamp}
        }
        actual_parsed_msg = cn.parse_raw_msg(raw_msg=test_raw_msg)
        assert actual_parsed_msg == expected_parsed_msg

    def test_yaml_parsed_correctly(self):
        os.environ["PARSE_AS"] = "YAML"
        cn = Connector(version=__version__)

        # A message that allows us to differtiate between encodings due to
        # non ASCII characters.
        test_msg_obj = {
            "dummy_dp": {"sensor_1": 2.0, "sensor_2": True, "sensor_3": "A string.",}
        }
        timestamp = 1618256642000

        test_raw_msg = {
            "payload": {
                "raw_message": str(yaml.dump(test_msg_obj).encode()),
                "timestamp": timestamp,
            },
        }
        expected_parsed_msg = {
            "payload": {"parsed_message": test_msg_obj, "timestamp": timestamp}
        }
        actual_parsed_msg = cn.parse_raw_msg(raw_msg=test_raw_msg)
        assert actual_parsed_msg == expected_parsed_msg


class TestSendCommand(unittest.TestCase):
    pass
