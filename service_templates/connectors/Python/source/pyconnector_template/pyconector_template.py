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
        msg["timestamp"] = ts_utc_now

        self.mqtt_client.publish(payload=json.dumps(msg))

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
        """
        raise NotImplementedError("receive_raw_msg has not been implemented.")