#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import os
import json
import logging
from re import L


from dotenv import load_dotenv, find_dotenv
import asyncio
import websockets
from datetime import datetime
from ocpp.routing import on
from ocpp.v16 import ChargePoint as OCPPChargePoint
from ocpp.v16 import call_result
from ocpp.v16 import call
from pyconnector_template.pyconector_template import SensorFlow as SFTemplate
from pyconnector_template.pyconector_template import ActuatorFlow as AFTemplate
from pyconnector_template.pyconector_template import Connector as CTemplate
from pyconnector_template.dispatch import DispatchInInterval
from pyconnector_template.dispatch import DispatchOnce


logger = logging.getLogger("pyconnector")
logger.setLevel(os.getenv('LOGLEVEL'))

class SensorFlow(SFTemplate):
    """
    Bundles all functionality to handle sensor messages.

    This is a template for a SensorFlow class, i.e. one that holds all
    functions that are necessary to handle messages from the device(s)
    towards the message broker. The methods could also be implemented
    into the Connector class, but are seperated to support clarity.

    Overload these functions
    ------------------------
    In order to transform this class into operational code you need
    to inherit from it and overload the following methods:
     - receive_raw_msg
     - parse_raw_msg

    Connector Methods
    -----------------
    The connector must provide the following methods to allow correct
    operation of the methods in this class:
     - _update_available_datapoints

    Connector Attributes
    --------------------
    The following attributes must be set up by the connector to
    allow these methods to run correctly:

    mqtt_client : class instance.
        Initialized Mqtt client library with signature of paho mqtt.
    SEND_RAW_MESSAGE_TO_DB : string
        if SEND_RAW_MESSAGE_TO_DB == "TRUE" will send raw message
        to designated DB via MQTT.
    MQTT_TOPIC_RAW_MESSAGE_TO_DB : string
        The topic which on which the raw messages will be published.
    datapoint_map : dict of dict.
        Mapping from datapoint key to topic. Is generated by the AdminUI.
        Looks e.e. like this:
            datapoint_map = {
                "sensor": {
                    "Channel__P__value__0": "example-connector/msgs/0001",
                    "Channel__P__unit__0": "example-connector/msgs/0002",
                },
                "actuator": {
                    "example-connector/msgs/0003": "Channel__P__setpoint__0",
                }
            }
        Note thereby that the keys "sensor" and "actuator"" must alaways be
        present, even if the child dicts are empty.
    """

    def receive_raw_msg(self, raw_data=None):
        """
        Functionality to receive a raw message from device.

        Poll the device/gateway for data and transforms this raw data
        into the format epxected by run_sensor_flow. If the device/gateway
        uses some protocol that pushes data, the raw data should be passed
        as the raw_data argument to the function.

        Parameters
        ----------
        raw_data : TYPE, optional
            Raw data of device/gateway if the device pushes and is not
            pulled for data. The default is None.

        Returns
        -------
        msg : dict
            The message object containing the raw unprocessed data.
            Should be formated like this:
                msg = {
                    "payload": {
                        "raw_message": <the raw data>
                    }
                }
            E.g.
                msg = {
                    "payload": {
                        "raw_message": "device_1:{sensor_1:2.12,sensor_2:3.12}"
                    }
                }
        """
        msg = {
            "payload":  {
                "raw_message": raw_data
            }
        }
        return msg

    def parse_raw_msg(self, raw_msg):
        """
        Functionality to receive a raw message from device.

        Poll the device/gateway for data and transforms this raw data
        into the format epxected by run_sensor_flow. If the device/gateway
        uses some protocol that pushes data, the raw data should be passed
        as the raw_data argument to the function.

        Be aware: All keys in the output message should be strings. All values
        should be converted be strings, too.

        Parameters
        ----------
        raw_msg : dict.
            Raw msg with data from device/gateway. Should be formated like:
                msg = {
                    "payload": {
                        "raw_message": <the raw data>,
                        "timestamp": <milliseconds since epoch>
                    }
                }

        Returns
        -------
        msg : dict
            The message object containing the parsed data as python dicts from
            dicts strucuture.
            Should be formated like this:
                msg = {
                    "payload": {
                        "parsed_message": <the parsed data as object>,
                        "timestamp": <milliseconds since epoch>
                    }
                }
            E.g:
                msg = {
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
        """
        timestamp = raw_msg["payload"]["timestamp"]
        raw_message = raw_msg["payload"]["raw_message"]
        parsed_message = raw_message
        msg = {
            "payload": {
                "parsed_message": parsed_message,
                "timestamp": timestamp
            }
        }
        return msg


class ActuatorFlow(AFTemplate):
    """
    Bundles all functionality to handle actuator messages.

    This is a template for a ActuatorFlow class, i.e. one that holds all
    functions that are necessary to handle messages from the message
    broker towards the devices/gateway. The methods could also be implemented
    into the Connector class, but are seperated to support clarity.

    Overload these functions
    ------------------------
    In order to transform this class into operational code you need
    to inherit from it and overload the following methods:
     - send_command

    Connector Attributes
    --------------------
    The following attributes must be set up by the connector to
    allow these methods to run correctly:

    datapoint_map : dict of dict.
        Mapping from datapoint key to topic. Is generated by the AdminUI.
        Looks e.e. like this:
            datapoint_map = {
                "sensor": {
                    "Channel__P__value__0": "example-connector/msgs/0001",
                    "Channel__P__unit__0": "example-connector/msgs/0002",
                },
                "actuator": {
                    "example-connector/msgs/0003": "Channel__P__setpoint__0",
                }
            }
        Note thereby that the keys "sensor" and "actuator"" must alaways be
        present, even if the child dicts are empty.
    """

    def send_command(self, datapoint_key, datapoint_value):
        """
        Send message to target device, via gateway if applicable.

        Parameters
        ----------
        datapoint_key : string.
            The internal key that is used by device/gateway to identify
            the datapoint.
        datapoint_value : string.
            The value that should be sent to the datapoint.
        """
        ocpp_method = datapoint_key.split("__")[0]
        # Call write_method with parsed (aka. decoded)
        command_method = getattr(self.cp, ocpp_method)  

        future = asyncio.run_coroutine_threadsafe(command_method(datapoint_value), self.loop_server)
        result = future.result()      
        logger.debug(
            result
        )


class ChargePoint(OCPPChargePoint):

    def __init__(self, cp_id, ws, sensor_flow_handler):
        super().__init__(cp_id, ws)
        self.sensor_flow_handler = sensor_flow_handler

    @on('BootNotification')
    def on_boot_notification(self, charge_point_vendor, charge_point_model, **kwargs):
        message = {
            "message": "BootNotification",
            "charge_point_vendor": charge_point_vendor,
            "charge_point_model": charge_point_model
        }
        logger.debug(
            "Charging station sent boot notification %s,",
            *(
                message
            )
        )
        self.sensor_flow_handler(message)

        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status="Accepted"
        )

    @on('MeterValues')
    def on_meter_value(self, connector_id, meter_value):
        message = {
            "message": "MeterValues",
            "connector_id": connector_id,
            "meter_value": meter_value
        }
        self.sensor_flow_handler(message)
        return call_result.MeterValuesPayload()

    @on('Heartbeat')
    def on_heartbeat(self):
        self.sensor_flow_handler({"message": "Heartbeat"})
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + "Z"
        )

    @on('Authorize')
    def on_authorize(self, id_tag):
        message = {
            "message": "Authorize",
            "id_tag": id_tag
        }
        return call_result.AuthorizePayload(
            id_tag_info={
                "status": 'Accepted'
            }
        )

    @on('StartTransaction')
    def on_start_transaction(self, connector_id, id_tag, timestamp, meter_start, reservation_id):
        return call_result.StartTransactionPayload(
            id_tag_info={
                "status": 'Accepted'
            },
            transaction_id=int(1)
        )

    @on('StopTransaction')
    def on_stop_transaction(self, transaction_id, id_tag, timestamp, meter_stop):
        return call_result.StopTransactionPayload()

    @on('StatusNotification')
    def on_status_notification(self, connector_id, error_code, status, timestamp):
        message = {
            "message": "StatusNotification",
            "connector_id": connector_id,
            "error_code": error_code,
            "status": status
        }
        self.sensor_flow_handler(message)

        print(connector_id, error_code, status, timestamp)
        return call_result.StatusNotificationPayload()

    @on('LogStatusNotification')
    def on_log_status_notification(self, status, request_id, **kwargs):
        print(f"status is {status} \n")
        #print(status, request_id)

    async def execute_unlock_connector(self):
        request = call.UnlockConnectorPayload(
            connector_id=1
        )
        response = await self.call(request)

    async def execute_get_composite_schedule(self):
        request = call.GetCompositeSchedulePayload(
            connector_id=1,
            duration=5,
            charging_rate_unit="W"
        )
        response = await self.call(request)
        composite_schedule = {
            "status": response.status,
            "schedule_start": response.schedule_start,
            "charging_schedule": response.charging_schedule
        }
        print(composite_schedule)
        return composite_schedule

    async def execute_trigger_message(self):
        request = call.TriggerMessagePayload(
            requested_message='MeterValues',
            connector_id=1
        )
        response = await self.call(request)

    async def execute_send_charging_profile(self, value):
        charging_profile = {"ChargingSchedule": {
            'chargingRateUnit':'W',
            'chargingSchedulePeriod': {
                'startPeriod': datetime.now().isoformat(),
                'limit':float(value)
            }
        }}
        request = call.SetChargingProfilePayload(
            connector_id=1, cs_charging_profiles=charging_profile)
        response = await self.call(request)
        if response.status == 'Accepted':
            return 'Profile acceped by charging station'
        else:
            return 'Profile not acceped by charging station'


class Connector(CTemplate, SensorFlow, ActuatorFlow):
    """
    The generic logic of the connector.

    It should not be necessary to overload any of these methods nor
    to call any of those apart from __init__() and run().

    Configuration Attributes
    ------------------------
    Confiugration will be populated from environment variables on init.
    CONNECTOR_NAME : string
        The name of the connector instance as seen by the AdminUI.
    MQTT_TOPIC_LOGS : string
        The topics used by the log handler to publish log messages on.
    MQTT_TOPIC_HEARTBEAT : string
        The topics used by the connector to publish heartbeats on.
    MQTT_TOPIC_AVAILABLE_DATAPOINTS : string
        The topic on which the available datapoints will be published.
    MQTT_TOPIC_DATAPOINT_MAP : string
        The topic the connector will listen on for datapoint maps
    SEND_RAW_MESSAGE_TO_DB : string
        if SEND_RAW_MESSAGE_TO_DB == "TRUE" will send raw message
        to designated DB via MQTT. This is a string and not a bool as
        environment variables are always strings.
    MQTT_TOPIC_RAW_MESSAGE_TO_DB : string
        The topic which on which the raw messages will be published.
    DEBUG : string
        if DEBUG == "TRUE" will log debug message to, elso loglevel is info.

    Computed Attributes
    -------------------
    These attriubutes are created by init and are then dynamically used
    by the Connector.
    mqtt_client : class instance.
        Initialized Mqtt client library with signature of paho mqtt.
    available_datapoints : dict of dict.
        Lists all datapoints known to the connector and is sent to the
        AdminUI. Actuator datapoints must be specified manually. Sensor
        datapoints are additionally automatically added once a value for
        a new datapoint is received. The object contains the connector
        internal key and a sample and value looks e.g. like this:
            available_datapoints = {
                "sensor": {
                    "Channel__P__value__0": 0.122,
                    "Channel__P__unit__0": "kW",
                },
                "actuator": {
                    "Channel__P__setpoint__0": 0.4,
                }
            }
    datapoint_map : dict of dict.
        Mapping from datapoint key to topic. Is generated by the AdminUI.
        Looks e.e. like this:
            datapoint_map = {
                "sensor": {
                    "Channel__P__value__0": "example-connector/msgs/0001",
                    "Channel__P__unit__0": "example-connector/msgs/0002",
                },
                "actuator": {
                    "example-connector/msgs/0003": "Channel__P__setpoint__0",
                }
            }
        Note thereby that the keys "sensor" and "actuator"" must alaways be
        present, even if the child dicts are empty.
    """

    def __init__(self, *args, **kwargs):

        load_dotenv(find_dotenv(), verbose=True, override=False)
        self.ocpp_port = os.getenv("OCPP_PORT")
        self.ocpp_config = os.getenv("OCPP_CONFIG")

        # parse actuator datapoints from config
        self.ocpp_command_method_names = [
            k for k in self.ocpp_config if "execute_" in k
        ]

        kwargs["DeviceDispatcher"] = DispatchOnce
        kwargs["device_dispatcher_kwargs"] = {
            "target_func": self.sync_wrapper_run_ocpp_server
        }
        # Sensor datapoints will be added to available_datapoints automatically
        # once they are first appear in run_sensor_flow method. It is thus not
        # necessary to specify them here. actuator datapoints in contrast must
        # be specified here.
        kwargs["available_datapoints"] = {
            "sensor": {},
            "actuator": self.compute_actuator_datapoints()
        }

        CTemplate.__init__(self, *args, **kwargs)


    def compute_actuator_datapoints(self):
        actuator_temp = {}
        for ocpp_method in self.ocpp_command_method_names:
            datapoint = ocpp_method + "__"
            actuator_temp.update({datapoint: "0"})
        return actuator_temp

    def sync_wrapper_run_ocpp_server(self):
        logger.debug('Starting Server by DeviceDispatcher')
        asyncio.run(self.run_ocpp_server())

    def loop_in_thread_server(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_ocpp_server())

    async def run_ocpp_server(self):
        self.server = await websockets.serve(
            self.on_connect,
            '0.0.0.0',
            self.ocpp_port,
            subprotocols=['ocpp1.6']
        )
        logging.info("Server started successfully")

        await self.server.wait_closed()

    # handler is executed on every new connection
    async def on_connect(self, websocket, path):
        """ For every new charge point that connects, create a ChargePoint instance
        and start listening for messages.
        """
        charge_point_id = path.strip('/')
        self.cp = ChargePoint(charge_point_id, websocket, sensor_flow_handler=self.run_sensor_flow)
        logger.debug(f'charging point connected: {charge_point_id}')

        await self.cp.start()


    def close_server(self):
        logger.info("Closing ocpp server")
        future = asyncio.run_coroutine_threadsafe(
            self.server.close(), self.loop_server)
        result = future.result()


if __name__ == "__main__":
    connector = Connector()
    connector.run()
