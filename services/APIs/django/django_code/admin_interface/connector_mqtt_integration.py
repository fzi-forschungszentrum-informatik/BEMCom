import json
import logging

from paho.mqtt.client import Client
from django.conf import settings
from django.db import connection

from admin_interface import models
from admin_interface.utils import datetime_from_timestamp

logger = logging.getLogger(__name__)


class ConnectorMQTTIntegration():

    _brokers = list()

    def __init__(self, mqtt_client=Client):
        """
        TODO: Use importlib.import_module('paho.mqtt.client.Client')
        """
        logger.info('Starting up Connector MQTT Integration.')

        # The configuration for connecting to the broker.
        connect_kwargs = {
            'host': settings.MQTT_BROKER['host'],
            'port': settings.MQTT_BROKER['port'],
        }
        #print('host: {}, port: {}'.format(connect_kwargs['host'], connect_kwargs['port']))

        # The topics dict used for subscribing and message routing.
        self.topics = self.compute_topics()

        # The private userdata, used by the callbacks.
        userdata = {
            'models': models,
            'connect_kwargs': connect_kwargs,
            'topics': self.topics,
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        # Start look in background process.
        self.client.loop_start()

        self.connected_topics = {}
        for topic in self.topics:
            # use QOS=2, expect messages once and only once.
            # No duplicates in log files etc.
            self.client.subscribe(topic, 2)

        ConnectorMQTTIntegration._brokers.append(self)

    @classmethod
    def get_broker(cls):
        return cls._brokers

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
            - mqtt_topic_datapoint_map

        """
        topics = {}
        message_types = [
            'mqtt_topic_logs',
            'mqtt_topic_heartbeat',
            'mqtt_topic_available_datapoints',
            'mqtt_topic_datapoint_map',
            'mqtt_topic_datapoint_message_wildcard'
        ]

        for connector in models.Connector.objects.all():
            for message_type in message_types:
                topic = getattr(connector, message_type)
                topics[topic] = (connector, message_type)
        return topics

    def integrate_new_connector(self, connector, message_types):
        for message_type in message_types:
            topic = getattr(connector, message_type)
            self.topics[topic] = (connector, message_type)
            self.client.subscribe(topic, 2)

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
        logger.info('got message on topic %s', msg.topic)
        if message_type == 'mqtt_topic_logs':
            timestamp = datetime_from_timestamp(payload['timestamp'])
            if not models.ConnectorLogEntry.objects.filter(
                    connector=connector,
                    timestamp=timestamp).exists():
                try:
                    _ = models.ConnectorLogEntry(
                        connector=connector,
                        timestamp=timestamp,
                        msg=payload['msg'],
                        emitter=payload['emitter'],
                        level=payload['level'],
                    ).save()
                except Exception:
                    logger.exception('Exception while writing Log into DB.')
                    # This raise will be caught by paho mqtt. It should not though.
                    raise

        if message_type == 'mqtt_topic_heartbeat':
            # TODO: Update the entry Instead of inserting one.
            try:
                _ = models.ConnectorHeartbeat(
                    connector=connector,
                    last_heartbeat=datetime_from_timestamp(
                        payload['this_heartbeats_timestamp']
                    ),
                    next_heartbeat=datetime_from_timestamp(
                        payload['next_heartbeats_timestamp']
                    ),
                ).save()
            except Exception:
                logger.exception('Exception while writing heartbeat into DB.')
                # This raise will be caught by paho mqtt. It should not though.
                raise

        if message_type == 'mqtt_topic_available_datapoints':
            # TODO: Check how many of those entries exist already.
            for datapoint_type in payload:
                #weird_value_string = ""

                for key, example in payload[datapoint_type].items():
                    # Check if this available datapoint already exists in database
                    # TODO: Update entry if type or example value changes for a given key instead of creating a new object
                    if not models.ConnectorAvailableDatapoints.objects.filter(
                            connector=connector,
                            datapoint_key_in_connector=key).exists():
                        try:
                            _ = models.ConnectorAvailableDatapoints(
                                connector=connector,
                                datapoint_type=datapoint_type,
                                datapoint_key_in_connector=key,
                                datapoint_example_value=example,
                            ).save()
                        except Exception:
                            logger.exception(
                                'Exception while writing available datapoint into '
                                'DB.'
                            )
                    # TODO: remove condition after string has been fixed
                    # TODO: create with with correct device and unit
                    if True: #key.startswith("soap"):
                        if not models.Datapoint.objects.filter(datapoint_key_in_connector=key).exists():
                            # print("Get device")
                            # device = models.Device.objects.filter(device_name="heatcontrol")[0]
                            # print(device.device_name)
                            try:
                                _ = models.Datapoint(
                                    datapoint_key_in_connector=key,
                                ).save()
                            except Exception:
                                logger.exception(
                                    'Exception while writing datapoint into DB.'
                                )
                    else:
                        pass #weird_value_string += example
                #print(weird_value_string)

        if message_type == 'mqtt_topic_datapoint_map':
            for datapoint_type in payload:
                for key, topic in payload[datapoint_type].items():
                    # Check if this mapping already exists in database
                    # TODO: Update entry if mapping changes instead of creating a new object
                    if not models.ConnectorDatapointTopicMapper.objects.filter(
                            datapoint_type=datapoint_type,
                            datapoint_key_in_connector=key,
                            mqtt_topic=topic).exists():
                        try:
                            _ = models.ConnectorDatapointTopicMapper(
                                connector=connector,
                                datapoint_type=datapoint_type,
                                datapoint_key_in_connector=key,
                                mqtt_topic=topic,
                                subscribed=False
                            ).save()
                        except Exception:
                            logger.exception(
                                'Exception while writing datapoint map into DB.'
                            )
            if message_type == 'mqtt_topic_datapoint_message_wildcard':
                print(payload)


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
    def on_subscribe(client, userdata, mid, granted_qos):
        logger.info('Subscribed: %s, %s', mid, granted_qos)
        # TODO: Set subscription status of av. datapoint here?
