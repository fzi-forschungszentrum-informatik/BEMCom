#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a template for building BEMCom connectors with Python.

The control flow and concepts are very similar to the Node-RED connector
template. You might want to instpect the Main flow of the Node-RED connector
template first to familiarize yourself with these.
"""
import json
from datetime import datetime

from paho.mqtt.client import Client


class SensorFlow():
    """
    Bundles all functionality to handle sensor messages.

    This is a template for a SensorFlow class, i.e. one that holds all
    functions that are necessary to handle messages from the device(s)
    towards the message broker. The methods could also be implemented
    into the Connector class, but are seperated to support clarity.

    In order to transform this class into operational code you need
    to inherit from it and overload the following methods:
        TODO
    """

    def run_sensor_flow(self, raw_data=None):
        """
        Processes data received from a device/gateway.

        Parameters
        ----------
        raw_data : TYPE, optional
            Raw data of device/gateway if the device pushes and is not
            pulled for data. The default is None.

        Returns
        -------
        None.

        """
        msg = self.receive_raw_msg(raw_data=raw_data)

        # Add receival timestamp in milliseconds since epoch.
        # (Following the message format.)
        ts_utc_now = round(datetime.timestamp(datetime.utcnow()) * 1000)
        msg["payload"]["timestamp"] = ts_utc_now

        # Send raw msg to raw message DB if activated in settings.
        # Handle bytes, as these are not JSON serializable.
        if self.SEND_RAW_MESSAGE_TO_DB:
            payload = msg["payload"]
            if isinstance(payload["raw_message"], (bytes, bytearray)):
                payload["raw_message"] = {
                    "bytes": payload["raw_message"].decode()
                }

            topic = self.MQTT_TOPIC_RAW_MESSAGE_TO_DB
            self.mqtt_client.publish(
                payload=json.dumps(payload),
                topic=topic,
                qos=2,  # Ensures the message is received by the raw msg DB.
            )

        # Parse raw content to dict of dict.
        msg = self.parse_raw_msg(self, raw_msg=msg)

        # Flatten the parsed message to a single level dict.
        msg = self.flatten_parsed_msg(self, parsed_msg=msg)

        # Check if we found new datapoints in this message and need to
        # send an update to the AdminUI.
        self.update_available_datapoints(flattened_msg=msg)

        # Publish values of datapoints that have been selected for such
        # within the AdminUI.
        self.filter_and_publish_datapoint_values(flattened_msg=msg)


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
        raise NotImplementedError("receive_raw_msg has not been implemented.")

    def parse_raw_msg(self, raw_msg):
        """
        Functionality to receive a raw message from device.

        Poll the device/gateway for data and transforms this raw data
        into the format epxected by run_sensor_flow. If the device/gateway
        uses some protocol that pushes data, the raw data should be passed
        as the raw_data argument to the function.

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
        raise NotImplementedError("parse_raw_msg has not been implemented.")