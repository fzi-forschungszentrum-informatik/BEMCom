#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import os
import json

from pyconnector_template.pyconector_template import SensorFlow, Connector
from pyconnector_template.pyconector_template import ActuatorFlow
from pyconnector_template.dispatch import DispatchInInterval


# Here is our pseudo device which is a demo for a real device that allows
# reading datapoints, and setting actuators values by overwrting the
# datapoint values in the dict.
pseudo_device = {
    "data": json.dumps({
        "device_1": {
            "temperature": "22.3",
            "temperature_setpoint": "21.5",
            "status": "ok",
        },
        "device_2" : {
            "temperature": "18.1",
            "temperature_setpoint": "17.0",
            "status": "battery low",
        },
    })
}

class DemoSensorFlow(SensorFlow):
    """
    A simple example to illustrate the schematic usage of SensorFlow to read
    data from a device or gateway.
    """

    def receive_raw_msg(self, raw_data=None):
        """
        Demo for reading raw data from device/gateway by loading data
        from pseudo_device dict.

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
        """
        # Would open the connection to the device here and read out the data.
        raw_message = pseudo_device["data"]

        # Build the expected output message format.
        msg = {
            "payload": {
                "raw_message": raw_message,
            }
        }

        return msg

    def parse_raw_msg(self, raw_msg):
        """
        Parse the demo raw_message by loading the object from json.

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
        msg = raw_msg
        raw_message = msg["payload"].pop("raw_message")

        # Here the actual parsing.
        parsed_message = json.loads(raw_message)

        # Rebuild the desired output format and return.
        msg["payload"]["parsed_message"] = parsed_message
        return msg


class DemoActuatorFlow(ActuatorFlow):
    """
    A simple example to illustrate the schematic usage of ActuatorFlow to
    write data to a device or gateway.
    """

    def send_command(self, datapoint_key, datapoint_value):
        """
        Demo for sending data to the actuator datapoint by storing the data
        in the pseudo_device.

        Parameters
        ----------
        datapoint_key : string.
            The internal key that is used by device/gateway to identify
            the datapoint.
        value : string.
            The value that should be sent to the datapoint.
        """
        # Would convert the actuator message to the format of the device.
        device_id = datapoint_key.split("__")[0]
        datapoint_id = datapoint_key.split("__")[0]

        # Would open the connection to the device here.
        # Depending on the device you might also want to maintain a permanent
        # connection to the device/gateway.
        connection = json.loads(pseudo_device["data"])

        # Would write the values to the device.
        connection[device_id][datapoint_id] = datapoint_value

        # Would close the connection.
        pseudo_device["data"] = json.dumps(connection)


class DemoConnector(Connector, DemoSensorFlow, DemoActuatorFlow):
    """
    TODO Write docstring.
    """
    pass

if __name__ == "__main__":

    # First expose some environment variables which are used to configure
    # the connector. Usually the connector is run in a docker container and
    # these variables are injected by docker. This setup allows us easier
    # orchestration applications with many connector services.
    os.environ["CONNECTOR_NAME"] = "python-demo-connector"
    os.environ["SEND_RAW_MESSAGE_TO_DB"] = "FALSE"
    os.environ["DEBUG"] = "FALSE"
    os.environ["MQTT_BROKER_HOST"] = "ipe-ht-02.fzi.de"
    os.environ["MQTT_BROKER_PORT"] = "1884"

    # Sensor datapoints will be added to available_datapoints automatically
    # once they are first appear in run_sensor_flow method. It is thus not
    # necessary to specify them automatically. Actuator datapoints must be
    # specified explicitly, including a demo value. Here we assume that the
    # temperature setpoints are actuator datapoints, while the remaining
    # values in pseudo_device are read only. The datapoint keys that are
    # used for the actuator keys here can be freely choosen, but need to
    # match what is expected in send_command.
    available_datapoints = {
        "sensor": {},
        "actuator": {
            "device_1__temperature_setpoint": "20.5",
            "device_2__temperature_setpoint": "20.5",
        }
    }
    # We need to specify a dispatcher that triggers the connection with
    # the device or gateway. Here we want to poll the device every 5 seconds
    # and use the DispatchInInterval interval thus, with suitable
    # configuration. The run method of the Connector will automatically
    # wire up target function of the dispatcher (run_sensor_flow) with
    # the dispatcher.
    DeviceDispatcher = DispatchInInterval
    device_dispatcher_kwargs = {"call_interval": 5}

    # Init the connector with the configuration and arguments defined above.
    demo_connector = DemoConnector(
        available_datapoints=available_datapoints,
        DeviceDispatcher=DeviceDispatcher,
        device_dispatcher_kwargs=device_dispatcher_kwargs,
    )

    demo_connector.run()