#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
__version__="0.4.0"

import os
import json
import socket
import logging
from time import sleep
from threading import Lock

from dotenv import load_dotenv, find_dotenv

from pyconnector_template.pyconnector_template import SensorFlow as SFTemplate
from pyconnector_template.pyconnector_template import ActuatorFlow as AFTemplate
from pyconnector_template.pyconnector_template import Connector as CTemplate
from pyconnector_template.dispatch import DispatchInInterval


logger = logging.getLogger("pyconnector")


class SensorFlow(SFTemplate):
    """
    Bundles all functionality to handle sensor messages.

    This is a template for a SensorFlow class, i.e. one that holds all
    functions that are necessary to handle messages from the device(s)
    towards the message broker. The methods could also be implemented
    into the Connector class, but are separated to support clarity.

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
        Initialized Mqtt client library with signature of paho MQTT.
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
        into the format expected by run_sensor_flow. If the device/gateway
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
            The message object containing the raw data as string. It must
            be a string to allow sending the raw_message object as JSON object
            to the raw message DB.
            Should be formatted like this:
                msg = {
                    "payload": {
                        "raw_message": <the raw data as string>
                    }
                }
            E.g.
                msg = {
                    "payload": {
                        "raw_message": "device_1:{sensor_1:2.12,sensor_2:3.12}"
                    }
                }
        """
        if not hasattr(self, "keba_socket"):
            # KEBA P30 uses UDP.
            self.keba_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Listen on all networking devices on anwsers from the charging
            # stations, as these always return to port 7090 according to
            # KEBAs UDP communication manual.
            self.keba_socket.bind(("0.0.0.0", 7090))
            # Configures socket to wait up to five seconds for data.
            self.keba_socket.settimeout(5)

        raw_message = {}
        for p30_name in self.keba_p30_charge_stations:
            p30_ip_addr_or_net_name = self.keba_p30_charge_stations[p30_name]
            # Lock the charge station to prevent parallel sending stuff
            # from actuator datapoints.
            p30_lock = self.keba_p30_locks[p30_name]
            p30_lock.acquire()
            logger.debug(
                "Requesting data from P30 charge station %s with "
                " network name or ip: %s",
                *(p30_name, p30_ip_addr_or_net_name)
            )

            try:
                # Try to request all the available data as suggested in
                # the KEBA UDP manual.
                raw_message[p30_name] = {}
                for request in ["report 1", "report 2", "report 3"]:
                    self.keba_socket.sendto(
                        request.encode(),
                        (p30_ip_addr_or_net_name, 7090)
                    )
                    # Some events like setting ena will trigger the charge
                    # station to automatically send some messages.
                    response = True
                    for i in range(21):
                        response = self.keba_socket.recv(4096)
                        if b"ID" in response:
                            break
                        logger.debug(
                            "Skipping non report response: %s",
                            response
                            )
                        if i >= 20:
                            raise RuntimeError(
                                "Received to many non-report responses from "
                                "charge station."
                            )

                    logger.debug(
                        "Request %s yielded response:\n%s",
                        *(request, response)
                    )
                    if isinstance(response, bytes):
                        response = response.decode()
                    raw_message[p30_name][request] = response
                    # This sleep is requested by the KEBA documentation
                    sleep(0.1)
            except socket.timeout:
                # This might recover later if the charge station is offline
                # or network errors have occured.
                logger.warning(
                    "No data received from P30 charge station %s.",
                    p30_name
                )
                continue

            except socket.gaierror:
                # This is a permanent error. Log, raise und thus shutdown.
                logging.error(
                    "Failed to send data to P30 charge station %s. "
                    "Is the network name or ip (%s) correct?"
                    *(p30_name, p30_ip_addr_or_net_name)
                )
                raise
            p30_lock.release()

        msg = {
            "payload": {
                "raw_message": raw_message
            }
        }
        return msg

    def parse_raw_msg(self, raw_msg):
        """
        Parses the values from the raw_message.

        This parses the raw_message into an object (in a JSON meaning, a
        dict in Python). The resulting object can be nested to allow
        representation of hierarchical data.

        Be aware: All keys in the output message should be strings. All values
        must be convertable to JSON.

        Parameters
        ----------
        raw_msg : dict.
            Raw msg with data from device/gateway. Should be formatted like:
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
            dicts structure. All keys should be strings. All value should be
            of type string, bool or numbers. Should be formatted like this:
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
                                "sensor_1": "test",
                                "sensor_2": 3.12,
                                "sensor_2": True,
                            }
                        },
                        "timestamp": 1573680749000
                    }
                }
        """
        raw_message = raw_msg["payload"]["raw_message"]
        parsed_message = {}
        for p30_name in raw_message:
            logger.debug(
                "Parsing raw data for P30 charge station %s.",
                p30_name
            )
            parsed_message[p30_name] = raw_message[p30_name]

        msg = {
            "payload": {
                "parsed_message": parsed_message,
                "timestamp": raw_msg["payload"]["timestamp"],
            }
        }
        return msg


class ActuatorFlow(AFTemplate):
    """
    Bundles all functionality to handle actuator messages.

    This is a template for a ActuatorFlow class, i.e. one that holds all
    functions that are necessary to handle messages from the message
    broker towards the devices/gateway. The methods could also be implemented
    into the Connector class, but are separated to support clarity.

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
        Note thereby that the keys "sensor" and "actuator"" must always be
        present, even if the child dicts are empty.
    """

    def send_command(self, datapoint_key, datapoint_value):
        """
        Send message to target device, via gateway if applicable.

        TODO: You may want to check here that the datapoint_values match
              the expected value ranges in the charge station manual.
        TODO: Could also add a warning if no confirmation is received.

        Parameters
        ----------
        datapoint_key : string.
            The internal key that is used by device/gateway to identify
            the datapoint.
        value : string.
            The value that should be sent to the datapoint.
        """
        logger.debug(
            "Processing actuator value msg for datapoint_key %s with value %s.",
            *(datapoint_key, datapoint_value)
        )

        # The name is stored in first part of the datapoint_key by
        # compute_actuator_datapoints.
        p30_name = datapoint_key.split("__")[0]
        p30_ip_addr_or_net_name = self.keba_p30_charge_stations[p30_name]

        # Lock the charge station to prevent parallel sending stuff
        # from actuator datapoints.
        p30_lock = self.keba_p30_locks[p30_name]
        p30_lock.acquire()

        try:
            keba_command = datapoint_key.split("__")[1]
            keba_payload = (keba_command + " " + datapoint_value).encode()
            self.keba_socket.sendto(
                keba_payload, (p30_ip_addr_or_net_name, 7090)
            )
            logger.debug(
                "Sent %s to %s",
                *(keba_payload, p30_ip_addr_or_net_name)
            )
            response = self.keba_socket.recv(4096)
            logger.debug("Received response for send_command: %s", response)
            # Prevent parallel communication until the required delay is over.
            if "ena" in datapoint_key:
                sleep(2)
            else:
                sleep(0.1)
        finally:
            p30_lock.release()


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
    These attributes are created by init and are then dynamically used
    by the Connector.
    mqtt_client : class instance.
        Initialized MQTT client library with signature of paho mqtt.
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
        Note thereby that the keys "sensor" and "actuator"" must always be
        present, even if the child dicts are empty.
    """

    def __init__(self, *args, **kwargs):
        """
        Init the inherited code from python_connector_template and add
        function to parse the special environment variable args to configure
        this connector.
        """
        # dotenv allows us to load env variables from .env files which is
        # convenient for developing. If you set override to True tests
        # may fail as the tests assume that the existing environ variables
        # have higher priority over ones defined in the .env file.
        load_dotenv(find_dotenv(), verbose=True, override=False)

        # We need to specify a dispatcher that triggers the connection with
        # the device or gateway. Here we want to poll the device with the
        # interval set in the POLL_SECONDS environment variable.
        # At each poll we want to execute the full run_sensor_flow
        # As this contains all the expected logic the connector should do
        # with sensor data.
        kwargs["DeviceDispatcher"] = DispatchInInterval
        kwargs["device_dispatcher_kwargs"] = {
            "call_interval": float(os.getenv("POLL_SECONDS")),
            "target_func": self.run_sensor_flow,
        }

        self.keba_p30_charge_stations = json.loads(
            os.getenv("KEBA_P30_CHARGE_STATIONS")
        )

        # One lock per charge station to prevent parallel access to the charge
        # stations. This is necessary to guerantee the delays that are demanded
        # by KEBA according to the UDP users guide.
        # It might also be necessary to prevent one charge station to
        # to be requested for data while we wait for a confirmation in
        # send_command for another. In this case we want only one lock
        # for all charge stations.
        lock = Lock()
        self.keba_p30_locks = {k: lock for k in self.keba_p30_charge_stations}

        # Sensor datapoints will be added to available_datapoints automatically
        # once they are first appear in run_sensor_flow method. It is thus not
        # necessary to specify them here, although it would be possible to
        # compute all possible datapoints beforehand based on
        # KEBA_P30_CHARGE_STATIONS
        kwargs["available_datapoints"] = {
            "sensor": {},
            "actuator": self.compute_actuator_datapoints(
                self.keba_p30_charge_stations
            ),
        }
        CTemplate.__init__(self, *args, **kwargs)

    def compute_actuator_datapoints(self, keba_p30_charge_stations):
        """
        Computes the key_in_connector and example_values for the actuator
        datapoints.

        It appears sufficient to expose the `ena`, `curr`, `setenergy` and
        `display` UDP methods. The other methods appear not strictly necessary
        and or may be replaced by BEMCom features, like `currtime`. Also
        set example_value to sane defaults, most of them are inspired by
        the example values in the KEBA UDP manual.

        Arguments:
        ----------
        keba_p30_charge_stations : dict
            The parsed version of the KEBA_P30_CHARGE_STATIONS JSON string
            as defined in the Readme.
        """
        actuator_datapoints = {}
        for cs_name in keba_p30_charge_stations:
            cs_ad = {
                "{}__ena".format(cs_name): "0",
                "{}__curr".format(cs_name): "63000",
                "{}__setenergy".format(cs_name): "100000",
                "{}__display".format(cs_name): "0 0 0 0 Hello$KEBA",
            }
            actuator_datapoints.update(cs_ad)
        return actuator_datapoints


if __name__ == "__main__":
    connector = Connector(version=__version__)
    connector.run()
