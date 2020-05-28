# -*- coding: utf-8 -*-
"""
This is the controller. See the Readme.md files for details.
"""
import os
import json
import logging

from dotenv import load_dotenv, find_dotenv
from paho.mqtt.client import Client

logger = logging.getLogger(__name__)


class Controller():

    def __init__(self, mqtt_broker_host, mqtt_broker_port, mqtt_config_topic,
                 mqtt_client=Client):
        # Below the normal startup and configration of this class.
        logger.info("Starting up Controller.")

        # The configuration for connecting to the broker.
        connect_kwargs = {
            "host": mqtt_broker_host,
            "port": mqtt_broker_port,
        }

        # The private userdata, used by the callbacks.
        userdata = {
            "connect_kwargs": connect_kwargs,
            "config_topic": mqtt_config_topic,
            "topic_index": {},
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        # Start loop in background process.
        self.client.loop_start()

        self.client.subscribe(mqtt_config_topic)

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        logger.info(
            'Connected to MQTT broker tcp://%s:%s',
            userdata['connect_kwargs']['host'],
            userdata['connect_kwargs']['port'],
        )

    @staticmethod
    def on_disconnect(client, userdata, rc):
        """
        Atempt Reconnecting if disconnect was not called from a call to
        client.disconnect().
        """
        if rc != 0:
            logger.info(
                'Lost connection to MQTT broker with code %s. Reconnecting',
                rc
            )
            client.connect(**userdata['connect_kwargs'])

    @staticmethod
    def on_message(client, userdata, msg):
        if msg.topic == userdata["config_topic"]:
            payload = json.loads(msg.payload)

            # Build up a topic index, linking from the topic to the topic of
            # the corresponding sensor value, the later is thereby used as
            # an id under which the last messages are stored.
            topic_index_new = {}
            for control_group in payload:
                sensor_value_topic = control_group["sensor"]["value"]
                actuator_setpoint_topic = control_group["actuator"]["setpoint"]
                actuator_schedule_topic = control_group["actuator"]["schedule"]

                topic_index_new[sensor_value_topic] = {
                    "id": sensor_value_topic,
                    "type": "sensor_value",
                }
                topic_index_new[actuator_setpoint_topic] = {
                    "id": sensor_value_topic,
                    "type": "actuator_setpoint",
                }
                topic_index_new[actuator_schedule_topic] = {
                    "id": sensor_value_topic,
                    "type": "actuator_schedule",
                }

            # Now use the index and the previous versionf of it to subscribe
            # to all topics for that are new in the last message and
            # unsubscribe from all topics that are no longer in the config.
            topic_index_old = userdata["topic_index"]
            new_topics = topic_index_new.keys() - topic_index_old.keys()
            deprecated_topics = topic_index_old.keys() - topic_index_new.keys()
            userdata["topic_index"] = topic_index_new
            for topic in new_topics:
                client.subscribe(topic, 0)
            for topic in deprecated_topics:
                client.unsubscribe(topic)

    def disconnect(self):
        """
        Shutdown gracefully -> Disconnect from broker and stop background loop.
        """
        self.client.disconnect()
        self.client.loop_stop()
        # Remove the client, so init can establish a new connection.
        del self.client


if __name__ == "__main__":
    # This is used in container mode to load the configuraiton from env
    # variables. While developing it should read the .env file located
    # in ../../
    load_dotenv(find_dotenv(), verbose=True)
    mqtt_broker_host = os.getenv('MQTT_BROKER_HOST')
    mqtt_broker_port = os.getenv('MQTT_BROKER_PORT')
    mqtt_config_topic = os.getenv('MQTT_TOPIC_CONTROLLED_DATAPOINTS')

    controller = Controller(
        mqtt_broker_host=mqtt_broker_host,
        mqtt_broker_port=mqtt_broker_port,
        mqtt_config_topic=mqtt_config_topic
    )
