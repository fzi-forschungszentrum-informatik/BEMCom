#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import asyncio
import logging
from time import sleep
import unittest
from unittest.mock import MagicMock, Mock, call
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call_result
from ocpp.v16 import call
from ocpp.routing import on
import websockets
from threading import Thread
import psutil
import pytest

from ..main import Connector


class RecursiveMagicMock(MagicMock):
    """
    Once initialized this mock just returns itself instead of new mock
    object. This allows you to test wether the init calls where correct.
    """

    def __call__(self, *args, **kwargs):
        # This is required that all mock calls are stored.
        _ = super().__call__(*args, **kwargs)
        return self


class ChargePoint(cp):

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model="Optimus",
            charge_point_vendor="The Mobility House"
        )
        # response vom Server 'BootNotificationResponse'
        response = await self.call(request)

    # Argument ist immer ein String 'Action'. Function decorator to mark function as handler for specific action. This hook's argument are the data that is in the payload for the specific action. The hook's return value should be the Payload for that specific action and is send to the caller.
    @on('SetChargingProfile')
    def on_charging_profile(self, evse_id, charging_profile, **kwargs):
        if charging_profile['charging_schedule']['charging_schedule_period'][0]['limit'] <= 6000:
            print('Maximalleistung: ',
                  charging_profile['charging_schedule']['charging_schedule_period'][0]['limit'], ' Watt')
            print('start Time: ',
                  charging_profile['charging_schedule']['start_schedule'])
            return call_result.SetChargingProfilePayload(
                status='Accepted'
            )
        else:
            return call_result.SetChargingProfilePayload(
                status='Rejected'
            )


class OcppTestClient():
    """
    A simple context manager that allows starting a TCP server in a process.
    """
    def __enter__(self):
        self.test_loop = asyncio.get_event_loop()
        async def connect_client():
            async with websockets.connect(
                'ws://localhost:9000/CP_1',
                subprotocols=['ocpp1.6']
            ) as ws:

                cp = ChargePoint('CP_1', ws)

                await asyncio.gather(cp.start(), cp.send_boot_notification())

        def loop_in_thread_server(loop):
            asyncio.loop_in_thread_server(loop)
            loop.run_until_complete(connect_client())

        self.thread = Thread(
            target=loop_in_thread_server,
            kwargs={"loop": self.test_loop},
            daemon=True,
        )
        self.thread.start()


    def __exit__(self, exception_type, exception_value, traceback):
        # Close the socket and stop thread after we are done
        #
        self.thread.join()
        # self.thread.join()

class TestClientConnection(unittest.TestCase):
    def setup_class(self):
        # Some generally useful kwargs for Connector to ensure that
        # run doesn't fail or blocks for ages.
        self.connector_default_kwargs = {
            "MqttClient": MagicMock,
            "heartbeat_interval": 0.05,
        }
        # Define test config.
        self.ocpp_profile = {
            "chargingProfileId": 0,
            "stackLevel": 5,
            "chargingProfileKind": "Absolute",
            "chargingProfilePurpose": "TxDefaultProfile",

            "chargingSchedule": {
                "startSchedule": "now",
                "chargingRateUnit": "W",
                "chargingSchedulePeriod": [
                    {
                        "startPeriod": 0,
                        "limit": 5000.1
                    }
                ]
            }
        }
        self.ocpp_config = {
            "execute_send_command": {}
        }
        # Prepare everything so we can init the class.
        os.environ["CP_IP"] = "localhost"
        os.environ["CP_PORT"] = "9000"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["OCPP_PROFILE"] = json.dumps(self.ocpp_profile)
        os.environ["OCPP_CONFIG"] = json.dumps(self.ocpp_config)


    def test_data_received_from_tcp(self):
        pass
        """
        Verify that we can receive data from TCP remote and that the
        raw data is forwarded as expected.

        BTW: This tests will always end with a error message like:
            ERROR    pyconnector:pyconector_template.py:726 Connector
                     main loop has caused an unexpected exception. Shuting down.
            This is the normal behaviour as
        """
        # Create a mock for the mqtt client that keeps the broker side
        # thread active for a bit, so it appears that the process is healthy.
    def fake_loop_forever():
        sleep(0.05)
        _MqttClient_mock = RecursiveMagicMock()
        _MqttClient_mock.loop_forever = fake_loop_forever

        cn = Connector()
        cn.run_sensor_flow = MagicMock()
        cn._MqttClient = _MqttClient_mock
        cn.run()
        OcppTestClient()

        # This will fail if run_sensor_flow hasn't been called
        # as expected or the raw_data has not been forwarded to
        # run_sensor_flow
        expected_raw_data = "test message".encode()
        print(cn.run_sensor_flow.call_args)
        actual_raw_data = cn.run_sensor_flow.call_args

        assert actual_raw_data == expected_raw_data


class TestReceiveRawMsg(unittest.TestCase):
    pass


class TestParseRawMsg(unittest.TestCase):
    pass


class TestSendCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Define test config.
        cls.ocpp_profile = {
            "chargingProfileId": 0,
            "stackLevel": 5,
            "chargingProfileKind": "Absolute",
            "chargingProfilePurpose": "TxDefaultProfile",

            "chargingSchedule": {
                "startSchedule": "now",
                "chargingRateUnit": "W",
                "chargingSchedulePeriod": [
                    {
                        "startPeriod": 0,
                        "limit": 5000.1
                    }
                ]
            }
        }

        # Prepare everything so we can init the class.
        os.environ["CP_IP"] = "localhost"
        os.environ["CP_PORT"] = "9000"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["OCPP_PROFILE"] = json.dumps(cls.ocpp_profile)
