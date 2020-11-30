#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a template for building BEMCom connectors with Python.

The control flow and concepts are very similar to the Node-RED connector
template. You might want to instpect the Main flow of the Node-RED connector
template first to familiarize yourself with these.
"""
import json
import logging
from datetime import datetime

from paho.mqtt.client import Client


logger = logging.getLogger("pyconnector template")


class SensorFlow():
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

    Attributes
    ----------
    The following attributes must be set up by the connector to
    allow these methods to run correctly:

    mqtt_client : class
        Mqtt client library with signature of paho mqtt.
    SEND_RAW_MESSAGE_TO_DB : bool
        Indicates whether the raw message will be sent to designated DB or not.
    MQTT_TOPIC_RAW_MESSAGE_TO_DB : string
        The topic which on which the raw messages will be published.
    datapoint_map : dict of dict.
        Mapping from datapoint key to topic. Looks e.e. like this:
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
        raise NotImplementedError("parse_raw_msg has not been implemented.")

    def flatten_parsed_msg(self, parsed_msg):
        """
        Flattens parsed object, i.e. transforms to single layer dict.

        Parameters
        ----------
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

        Returns
        -------
        msg : dict
            The message object containing the flattened data.
            Should be formated like this:
                msg = {
                    "payload": {
                        "flattened_message": <the flattend object>,
                        "timestamp": <milliseconds since epoch>
                    }
                }
            E.g:
                msg = {
                    "payload": {
                        "flattened_message": {
                            "device_1__sensor_1": "2.12",
                            "device_1__sensor_2": "3.12"
                        },
                        "timestamp": 1573680749000
                    }
                }
        """
        msg = parsed_msg

        unflat = msg["payload"].pop("parsed_message")
        unflat_next = {}
        flattened = {}

        while unflat:
            for k, v in unflat.items():
                # This is a value, stop iteration for this entry.
                if not isinstance(v, dict):
                    flattened[k] = v
                    continue

                # Here the value is another dict. Dig deeper.
                for k_child, v_child in v.items():
                    k_merged = "__".join([k, k_child])
                    unflat_next[k_merged] = v_child

            unflat = unflat_next
            unflat_next = {}

        msg["payload"]["flattened_message"] = flattened

        return msg


class Connector():

    def init(self, datapoint_map=None):


        if datapoint_map is None:
            self.datapoint_map = {"sensor": {}, "actuator": {}}
        else:
            self.validate_and_update_datapoint_map(datapoint_map)

    def validate_and_update_datapoint_map(self, datapoint_map_json):
        """
        Inspects a newly received datapoint_map and stores it if it is valid.

        This function is intended to be used directly within the on_message
        callback and takes thus a jsonized datapoint as input.

        Errors in datapoint_map format will be logged but not raised, as we
        expect it is better to continue running the connector with an outdated
        datapoint map then shutting it down.

        Parameters
        ----------
        datapoint_map_json : string
            datapoint_map to validate and store in JSON format.
        """
        datapoint_map = json.loads(datapoint_map_json)
        if not "sensor" in datapoint_map:
            logger.error("No sensor key in datapoint_map. Cancel update.")
            return
        if not "actuator" in datapoint_map:
            logger.error("No actuator key in datapoint_map. Cancel update.")
            return
        if not isinstance(datapoint_map["sensor"], dict):
            logger.error(
                "Sensor entry in datapoint_map contains contains no dict."
                "Cancel update."
            )
            return
        if not isinstance(datapoint_map["actuator"], dict):
            logger.error(
                "Actuator entry in datapoint_map contains contains no dict."
                "Cancel update."
            )
            return
        self.datapoint_map = datapoint_map


