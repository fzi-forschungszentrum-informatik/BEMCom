#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a template for building BEMCom connectors with Python.

The control flow and concepts are very similar to the Node-RED connector
template. You might want to inspect the Main flow of the Node-RED connector
template first to familiarize yourself with these.
"""
import os
import json
import time
import logging
from datetime import datetime, timezone

from paho.mqtt.client import Client
from dotenv import load_dotenv, find_dotenv

from .dispatch import DispatchOnce

# Log everything to stdout by default, i.e. to docker container logs.
LOGFORMAT = "%(asctime)s-%(funcName)s-%(levelname)s: %(message)s"
logging.basicConfig(format=LOGFORMAT, level=logging.DEBUG)
logger = logging.getLogger("pyconnector")


def timestamp_utc_now():
    """
    Returns the timestamp of the current UTC time in milliseconds.
    Rounded to full microseconds.
    """
    return round(datetime.now(tz=timezone.utc).timestamp() * 1000)


class MQTTHandler(logging.StreamHandler):
    """
    A logging handler that allows publishing log messages on a MQTT broker.
    """

    def __init__(self, mqtt_client, log_topic):
        """
        Set up Handler.

        Assumes that mqtt_client is already initialized, i.e. that the log
        handler can use it directly for publishing and does not need to
        connect or similar. The later is handled by the connector already,
        hence there is no need to reproduce this here.

        Parameters
        ----------
        mqtt_client : class instance.
            Initialized Mqtt client library with signature of paho MQTT.
        log_topic : string
            The topic on which this handler publishes the log messages.
        """
        super().__init__()
        self.mqtt_client = mqtt_client
        self.log_topic = log_topic

    def emit(self, record):
        """
        Publish log record on MQTT broker.

        Parameters
        ----------
        record : logging.LogRecord
            The record to publish.
        """
        log_msg = {
            "timestamp": timestamp_utc_now(),
            "msg": record.msg % record.args,
            "emitter": record.funcName,
            "level": record.levelno,
        }

        self.mqtt_client.publish(
            payload=json.dumps(log_msg),
            topic=self.log_topic,
            retain=True,
        )


class SensorFlow:
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
        Note thereby that the keys "sensor" and "actuator"" must always be
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
        """
        logger.debug("Calling receive_raw_msg with raw_data: %s", raw_data)
        msg = self.receive_raw_msg(raw_data=raw_data)

        # Stop if receive_raw_msg returned a message that is not intended
        # to be processed.
        if msg["payload"] is None:
            logger.debug(
                "Stopped run_sensor_flow for msg with empty payload after "
                "receive_raw_msg."
            )
            return

        # Add receival timestamp in milliseconds since epoch.
        # (Following the message format.)
        ts_utc_now = timestamp_utc_now()
        msg["payload"]["timestamp"] = ts_utc_now

        # Send raw msg to raw message DB if activated in settings.
        if self.SEND_RAW_MESSAGE_TO_DB == "TRUE":
            # Add version number of connector too, this allows us to identify
            # the used connector once reprocessing messages.
            #
            # The payload here is the payload of the internal message object,
            # which we don not want to modify to provide exactly the same
            # data as during the initial run while reprocessing the message.
            # Hence we add the connection version one level up.
            mqtt_payload = {
                "payload": msg["payload"].copy(),
                "connector_version": self.version,
            }
            topic = self.MQTT_TOPIC_RAW_MESSAGE_TO_DB
            # This fails if the raw_message is or contains bytes.
            # Convert raw_message to string in parse_raw_msg in such cases.
            self.mqtt_client.publish(
                payload=json.dumps(mqtt_payload),
                topic=topic,
                qos=2,  # Ensures the message is received by the raw msg DB.
            )

        # Parse raw content to dict of dict.
        logger.debug("Calling parse_raw_msg with raw_msg: %s", msg)
        msg = self.parse_raw_msg(raw_msg=msg)

        # Stop if receive_raw_msg returned a message that is not intended
        # to be processed.
        if msg["payload"] is None:
            logger.debug(
                "Stopped run_sensor_flow for msg with empty payload after "
                "parse_raw_msg."
            )
            return

        # Flatten the parsed message to a single level dict.
        logger.debug("Calling _flatten_parsed_msg with parsed_msg: %s", msg)
        msg = self._flatten_parsed_msg(parsed_msg=msg)

        # Check if we found new datapoints in this message and need to
        # send an update to the AdminUI.
        available_datapoints_update = {
            "actuator": {},
            "sensor": msg["payload"]["flattened_message"],
        }
        self._update_available_datapoints(
            available_datapoints=available_datapoints_update
        )

        # Publish values of datapoints that have been selected for such
        # within the AdminUI.
        logger.debug(
            "Calling _filter_and_publish_datapoint_values with "
            "flattened_msg: %s",
            msg,
        )
        self._filter_and_publish_datapoint_values(flattened_msg=msg)

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
            The message object containing the raw data. It must be
            JSON serializable (to allow sending the raw_message object as JSON
            object to the raw message DB). If the data received from the device
            or gateway cannot be packed to JSON directly (like e.g. for bytes)
            it must modified accordingly. Avoid manipulation of the data as much
            as possible, to prevent data losses when these operations fail.
            A simple solution may often be to cast the raw data to strings.
            Dict structures are fine, especially if created in this function,
            e.g. by iterating over many endpoints of one device.
            Set the value of payload to None if run_sensor_flow should be
            stopped for this message.
            Should be formatted like this:
                msg = {
                    "payload": {
                        "raw_message": <raw data in JSON serializable form>
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
            of type string, bool or numbers.
            Set the value of payload to None if run_sensor_flow should be
            stopped for this message.
            Should be formatted like this:
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
        raise NotImplementedError("parse_raw_msg has not been implemented.")

    def _flatten_parsed_msg(self, parsed_msg):
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

    def _filter_and_publish_datapoint_values(self, flattened_msg):
        """
        Generate and send value messages for selected datapoints.

        datapoints are selected via the datapoint_map attribute.

        Parameters
        ----------
        flattened_msg : dict
            The message object containing the flattened data.
            Should be formated like this:
                msg = {
                    "payload": {
                        "flattened_message": <the flattend object>,
                        "timestamp": <milliseconds since epoch>
                    }
                }
        """
        flattened_message = flattened_msg["payload"]["flattened_message"]
        for datapoint_key, datapoint_value in flattened_message.items():
            # Skip all not selected datapoints
            if datapoint_key not in self.datapoint_map["sensor"]:
                continue

            # The datapoint_value here must be convertible to a JSON.
            # If in doubt pack it into a string.
            timestamp = flattened_msg["payload"]["timestamp"]
            value_msg = {
                "value": datapoint_value,
                "timestamp": timestamp,
            }

            # Previously this method was expected to return strings only.
            # Now it accepts any datatype that is JSON serializable.
            # This is a fallback in case a connector parsed values which
            # are not JSON serializable.
            topic = self.datapoint_map["sensor"][datapoint_key]
            try:
                payload = json.dumps(value_msg)
            except TypeError:
                logger.warning(
                    "Encountered TypeError while serializing value message "
                    "for topic: %s",
                    topic,
                )
                value_msg = {
                    "value": str(datapoint_value),
                    "timestamp": timestamp,
                }
                payload = json.dumps(value_msg)

            self.mqtt_client.publish(
                topic=topic,
                payload=payload,
                retain=True,
            )


class ActuatorFlow:
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

    def run_actuator_flow(self, topic, value_msg_json):
        """
        Processes an actuator value message and triggers sending it to
        the actuator datapoint.

        Parameters
        ----------
        topic: string.
            The topic on which the msg has been received.
        value_msg_json : string.
            The value message that should be sent to the actuator encoded
            in JSON.
        """
        value_msg = json.loads(value_msg_json)

        # Extract the value and load the connector internal key for this msg.
        datapoint_value = value_msg["value"]
        datapoint_timestamp = value_msg["timestamp"]
        datapoint_key = self.datapoint_map["actuator"][topic]

        self.send_command(
            datapoint_key=datapoint_key,
            datapoint_value=datapoint_value,
            datapoint_timestamp=datapoint_timestamp,
        )

    def send_command(self, datapoint_key, datapoint_value, datapoint_timestamp):
        """
        Send message to target device, via gateway if applicable.

        Parameters
        ----------
        datapoint_key : string.
            The internal key that is used by device/gateway to identify
            the datapoint.
        value : string.
            The value that should be sent to the datapoint.
        """
        raise NotImplementedError("send_command has not been implemented.")


class Connector:
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
        if DEBUG == "TRUE" will log debug message to, else loglevel is info.

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

    def __init__(
        self,
        version,
        datapoint_map=None,
        available_datapoints=None,
        DeviceDispatcher=None,
        device_dispatcher_kwargs=None,
        MqttClient=Client,
        heartbeat_interval=30,
    ):
        """
        Parameters
        ----------
        version : string
            The version number of the connector, e.g. "0.21.1"
            The version number is stored in the raw message DB to allow
            reprocessing with the correct version.
        datapoint_map : dict of dicts, optional.
            The initial datapoint_map before updating per MQTT. Format is
            specified in the class attribute docstring above.
        available_datapoints : dict of dicts, optional.
            The initial available_datapoints object before updating per MQTT.
            Format is specified in the class attribute docstring above.
        DeviceDispatcher : Dispatcher class.
            A class with similar signature to the dispatchers located in
            pyconnector.dispatch. The device dispatcher is responsible
            for repeatedly polling the device/gateway for data or (or
            handling incoming data on push style connections).
            Defaults to None, and if None will not poll/receive any
            data from the device/gateway.
        device_dispatcher_kwargs : dict.
            Keyword arguments that will be provided to DeviceDispatcher
            on calling __init__. Defaults to {}.
        MqttClient : class.
            Uninitialized MQTT client library with signature of paho MQTT.
            Defaults to paho.mqtt.client.Client. Providing other clients
            is mostly useful for testing.
        heartbeat_interval : int/float.
            The time in seconds we wait between checking the dispatchers
            and sending a heartbeat signal. Defaults to 30 seconds.
        """
        # dotenv allows us to load env variables from .env files which is
        # convenient for developing. If you set override to True tests
        # may fail as the tests assume that the existing environ variables
        # have higher priority over ones defined in the .env file.
        # usecwd will make finding dotenvs relative to the derived connector
        # and not relative to this file, which is the default.
        load_dotenv(find_dotenv(usecwd=True), verbose=True, override=False)
        self.CONNECTOR_NAME = os.getenv("CONNECTOR_NAME") or "unknown-connector"
        self.SEND_RAW_MESSAGE_TO_DB = os.getenv("SEND_RAW_MESSAGE_TO_DB")
        self.DEBUG = os.getenv("DEBUG")
        self.MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
        self.MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))

        logger.info(
            "Initiating pyconnector.Connector class for: %s",
            self.CONNECTOR_NAME,
        )

        cn = self.CONNECTOR_NAME
        self.MQTT_TOPIC_LOGS = "%s/logs" % cn
        self.MQTT_TOPIC_HEARTBEAT = "%s/heartbeat" % cn
        self.MQTT_TOPIC_AVAILABLE_DATAPOINTS = "%s/available_datapoints" % cn
        self.MQTT_TOPIC_DATAPOINT_MAP = "%s/datapoint_map" % cn
        self.MQTT_TOPIC_RAW_MESSAGE_TO_DB = "%s/raw_message_to_db" % cn

        # Set the log level according to the DEBUG flag.
        if self.DEBUG != "TRUE":
            logger.info("Changing log level to INFO")
            for logger_name in logging.root.manager.loggerDict:
                logging.getLogger(logger_name).setLevel(logging.INFO)

        # Store the class arguments that are used for run later.
        logger.debug("Processing __init__ arguments.")
        self.version = version
        self._DeviceDispatcher = DeviceDispatcher
        if device_dispatcher_kwargs is None:
            device_dispatcher_kwargs = {}  # Apply default value.
        self._device_dispatcher_kwargs = device_dispatcher_kwargs
        self._MqttClient = MqttClient
        self._heartbeat_interval = heartbeat_interval

        # Updateing either of the two is not possible at this point as
        # the MQTT connection is not available yet.
        self._initial_datapoint_map = datapoint_map
        self._initial_available_datapoints = available_datapoints

        logger.debug("Finished Connector init.")

    def run(self):
        """
        Run the connector until SystemExit or Keyboard interrupt is received.
        (Or of course an exception occurred in the connector.)


        """
        logger.debug("Entering Connector run method")

        # Setup and configure connection with MQTT message broker.
        # Also wire through a reference to the Connector instance (self)
        # as this allows _handle_incoming_mqtt_msg to call Connector methods.
        logger.debug("Configuring MQTT connection")
        self.mqtt_client = self._MqttClient(userdata={"self": self})
        self.mqtt_client.on_message = self._handle_incoming_mqtt_msg
        self.mqtt_client.connect(
            host=self.MQTT_BROKER_HOST, port=self.MQTT_BROKER_PORT
        )

        # Execute the MQTT main loop in a dedicated thread. This is
        # similar to use loop_start of paho mqtt but allows us to use a
        # unfied concept to check whether all background processes are
        # still alive.
        def mqtt_worker(mqtt_client):
            try:
                mqtt_client.loop_forever()
            finally:
                # Gracefully terminate connection once the main program exits.
                mqtt_client.disconnect()

        logger.debug("Starting broker dispatcher with MQTT client loop.")
        broker_dispatcher = DispatchOnce(
            target_func=mqtt_worker,
            target_kwargs={"mqtt_client": self.mqtt_client},
        )
        broker_dispatcher.start()

        # This collects all running dispatchers. These are checked for health
        # in the main loop below.
        dispatchers = [broker_dispatcher]

        # Add MQTT Log handler if it isn't in there yet.
        if not any([isinstance(h, MQTTHandler) for h in logger.handlers]):
            mqtt_log_handler = MQTTHandler(
                mqtt_client=self.mqtt_client,
                log_topic=self.MQTT_TOPIC_LOGS,
            )
            logger.addHandler(mqtt_log_handler)

        # Now that the connection to the message broker exists, we can
        # initialize our datapoint registers.
        logger.debug("Initiating datapoint_map")
        self.datapoint_map = {"sensor": {}, "actuator": {}}
        if self._initial_datapoint_map is not None:
            self._validate_and_update_datapoint_map(
                datapoint_map_json=json.dumps(self._initial_datapoint_map)
            )

        logger.debug("Initiating available_datapoints")
        self.available_datapoints = {"sensor": {}, "actuator": {}}
        if self._initial_available_datapoints is not None:
            self._update_available_datapoints(
                available_datapoints=self._initial_available_datapoints
            )

        # We want to receive the latest datapoint_maps and it won't hurt
        # us too bad if we receive them multiple times. This can only be
        # executed after the datapoint_map is initialized, as any retained
        # datapoint map is else overwritten.
        self.mqtt_client.subscribe(topic=self.MQTT_TOPIC_DATAPOINT_MAP, qos=1)

        # Start up the device dispatcher if specified to poll/receive
        # data from the device or gateway.
        if self._DeviceDispatcher is None:
            logger.warning(
                "DeviceDispatcher is not set. Will not receive sensor "
                "datapoint values from device/gateway."
            )
        else:
            logger.debug("Starting device dispatcher")
            device_dispatcher_kwargs = self._device_dispatcher_kwargs
            if "target_func" not in device_dispatcher_kwargs:
                logger.warning(
                    "Did not find a target function (the target_func argument) "
                    "in device_dispatcher_kwargs. Without it the connector "
                    "would shut down immediatly. Using the default value of "
                    "self.run_sensor_flow ."
                )
                device_dispatcher_kwargs["target_func"] = self.run_sensor_flow
            device_dispatcher = self._DeviceDispatcher(
                **device_dispatcher_kwargs
            )
            device_dispatcher.start()
            dispatchers.append(device_dispatcher)

        # Start the main loop which we spend all the operation time in.
        logger.info("Connector online. Entering main loop.")
        try:
            while True:
                # Check that all dispatchers are alive, and if this is the
                # case assume that the connector operations as expected.
                if not all([d.is_alive() for d in dispatchers]):
                    # If one is not alive, see if we encountered an exception
                    # and raise it, as exceptions in threads are not
                    # automatically forwarded to the main program.
                    for d in dispatchers:
                        if d.exception is not None:
                            raise d.exception
                    # If no exception is found raise a custom on.
                    raise RuntimeError(
                        "At least one dispatcher thread is not alive, but no "
                        "exception was caught."
                    )

                    break
                self._send_heartbeat()
                time.sleep(self._heartbeat_interval)

        except (KeyboardInterrupt, SystemExit):
            # This is the normal way to exit the Connector. No need to log the
            # exception.
            logger.info(
                "Connector received KeyboardInterrupt or SystemExit"
                ", shuting down."
            )
        except:  # NOQA
            # This is execution when something goes really wrong.
            logger.exception(
                "Connector main loop has caused an unexpected exception. "
                "Shuting down."
            )
        finally:
            for dispatcher in dispatchers:
                # Ask the dispatcher (i.e. thread) to quit and give it
                # one second to execute any cleanup. Anything that takes
                # longer will be killed hard once the main program exits
                # as the dispatcher thread is expected to be a daemonic
                # thread.
                logger.debug("Terminating dispatcher %s", dispatcher)
                if dispatcher.is_alive():
                    dispatcher.terminate()
                dispatcher.join(1)
            logger.info("Connector shut down completed. Good bye.")

    @staticmethod
    def _handle_incoming_mqtt_msg(client, userdata, msg):
        """
        Handle incoming MQTT message by calling the appropriate methods.

        Essentially we need to distinguish between messages that contain
        a new datapoint_map and messages that carry values for actuator
        datapoints.

        This is the callback provided to the MQTT clients on_message
        method.

        Parameters
        ----------
        client : client : class.
            Initialized MQTT client library with signature of paho MQTT.
        userdata : dict.
            Must contain {"self": <connector class>}.
        msg : paho mqtt message class.
            The message to handle.
        """
        self = userdata["self"]
        logger.debug("Handling incoming MQTT message on topic: %s", msg.topic)
        if msg.topic == self.MQTT_TOPIC_DATAPOINT_MAP:
            self._validate_and_update_datapoint_map(
                datapoint_map_json=msg.payload
            )
        else:
            self.run_actuator_flow(topic=msg.topic, value_msg_json=msg.payload)

    def _validate_and_update_datapoint_map(self, datapoint_map_json):
        """
        Inspects a newly received datapoint_map and stores it if it is valid.

        This function is intended to be used directly within the on_message
        callback and takes thus a jsonized datapoint as input.

        Errors in datapoint_map format will be logged but not raised, as we
        expect it is better to continue running the connector with an outdated
        datapoint map then shutting it down.

        Finally, changes for actuator part of the map will also have an effect
        on the subscribed topics, as new entries may require the subscription
        of the new topic, or deprecated entries may trigger an unsubscribe.

        Parameters
        ----------
        datapoint_map_json : string
            datapoint_map to validate and store in JSON format.
            Format is specified in the class attribute docstring above.
        """
        logger.debug("Started _validate_and_update_datapoint_map")
        datapoint_map = json.loads(datapoint_map_json)
        if "sensor" not in datapoint_map:
            logger.error("No sensor key in datapoint_map. Cancel update.")
            return
        if "actuator" not in datapoint_map:
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

        # Update subscription for actuator datapoints.
        actuator_topics_new = set(datapoint_map["actuator"].keys())
        actuator_topics_old = set(self.datapoint_map["actuator"].keys())
        new_topics = actuator_topics_new.difference(actuator_topics_old)
        removed_topics = actuator_topics_old.difference(actuator_topics_new)
        for topic in removed_topics:
            self.mqtt_client.unsubscribe(topic=topic)
        for topic in new_topics:
            # Ensure actuator messages are delivered once and only once.
            self.mqtt_client.subscribe(topic=topic, qos=2)

        self.datapoint_map = datapoint_map

        if new_topics or removed_topics:
            logger.debug("Installed new datapoint_map %s", datapoint_map)

    def _update_available_datapoints(self, available_datapoints):
        """
        Updates the available_datapoint dict.

        Will always update the sample values but only send and update to the
        AdminUI if a new datapoint has been found.

        Parameters
        ----------
        available_datapoints : dict of dicts.
            Connector internal keys and example values for available_datapoints
            to store and optionally publish. Format is specified in the class
            attriubte docstring above.
        """
        available_datapoints_old = self.available_datapoints

        # Check if the update to available_datapoints introduces new keys
        new_keys_found = False
        for dpt in ["sensor", "actuator"]:
            existing_keys = set(available_datapoints_old[dpt].keys())
            updated_keys = set(available_datapoints[dpt].keys())
            if updated_keys.difference(existing_keys):
                new_keys_found = True
                break

        # Update the example values
        for dpt in ["sensor", "actuator"]:
            available_datapoints_old[dpt].update(available_datapoints[dpt])

        # Store the updated map
        self.available_datapoints = available_datapoints_old

        # Publish if new keys found.
        if new_keys_found:
            self.mqtt_client.publish(
                payload=json.dumps(self.available_datapoints),
                topic=self.MQTT_TOPIC_AVAILABLE_DATAPOINTS,
                retain=True,
            )

    def _send_heartbeat(self):
        """
        Send a heartbeat message to the MQTT broker.
        """
        ts_now = timestamp_utc_now()
        ts_next = round(ts_now + self._heartbeat_interval * 1000)
        heartbeat_msg = {
            "this_heartbeats_timestamp": ts_now,
            "next_heartbeats_timestamp": ts_next,
        }
        self.mqtt_client.publish(
            topic=self.MQTT_TOPIC_HEARTBEAT, payload=json.dumps(heartbeat_msg)
        )
