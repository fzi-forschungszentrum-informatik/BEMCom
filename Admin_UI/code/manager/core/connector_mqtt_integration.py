import json
import logging

from paho.mqtt.client import Client
from django.conf import settings

from core import models
from core.utils import datetime_from_timestamp

logger = logging.getLogger(__name__)


class ConnectorMQTTIntegration():

    def __init__(self, mqtt_client=Client):
        """
        """
        logger.info('Starting up Connector MQTT Integration.')

        # The configuration for connecting to the broker.
        connect_kwargs = {
            'host': settings.MQTT_BROKER['host'],
            'port': settings.MQTT_BROKER['port'],
        }

        # The topics dict used for subscribing and message routing.
        topics = self.compute_topics()

        # The private userdata, used by the callbacks.
        userdata = {
            'models': models,
            'connect_kwargs': connect_kwargs,
            'topics': topics,
        }

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        for topic in topics:
            # use QOS=2, expect messages once and only once.
            # No duplicates in log files etc.
            self.client.subscribe(topic, 2)

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        # Start look in background process.
        self.client.loop_start()

    def disconnect(self):
        """
        Shutdown gracefully -> Disconnect from broker and stop background loop.
        """
        self.client.disconnect()
        self.client.loop_stop()

    @staticmethod
    def compute_topics():
        """
        Computes a list of all topics associated with the currently
        registered Connecetors.

        Returns:
        --------
        topics: dict
            as <topic>: (<Connector object>, <message type>)
            with <message type> being on of the following:
            - mqtt_topic_logs
            - mqtt_topic_heartbeat
            - mqtt_topic_available_datapoints
        """
        topics = {}
        message_types = [
            'mqtt_topic_logs',
            'mqtt_topic_heartbeat',
            'mqtt_topic_available_datapoints',
        ]

        for connector in models.Connector.objects.all():
            for message_type in message_types:
                topic = getattr(connector, message_type)
                topics[topic] = (connector, message_type)
        return topics

    @staticmethod
    def on_message(client, userdata, msg):
        """
        Handle incomming mqtt messages by writing to appropriate DB tables.

        Arguments:
        ----------
        See paho mqtt documentation.
        """
        topics = userdata['topics']
        models = userdata['models']

        connector, message_type = topics[msg.topic]
        payload = json.loads(msg.payload)

        if message_type == 'mqtt_topic_logs':
            _ = models.ConnectorLogEntry(
                connector=connector,
                timestamp=datetime_from_timestamp(payload['timestamp']),
                msg=payload['msg'],
                emitter=payload['emitter'],
                level=payload['level'],
            ).save()

        if message_type == 'mqtt_topic_heartbeat':
            """
            TODO: Update the entry Instead of inserting one.
            """
            _ = models.ConnectorHearbeat(
                connector=connector,
                last_heartbeat=datetime_from_timestamp(
                    payload['this_heartbeats_timestamp']
                ),
                next_heartbeat=datetime_from_timestamp(
                    payload['next_heartbeats_timestamp']
                ),
            )

        if message_type == 'mqtt_topic_available_datapoints':
            """
            TODO: Check how many of those entries exist already.
            """
            for datapoint_type in payload:
                for key, example in payload[datapoint_type].items():
                    _ = models.ConnectorAvailableDatapoints(
                        connector=connector,
                        datapoint_type=datapoint_type,
                        datapoint_key_in_connector=key,
                        datapoint_example_value=example,
                    )

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

