import json
import logging

from paho.mqtt.client import Client
from django.conf import settings

from admin_interface import models
from admin_interface.utils import datetime_from_timestamp

logger = logging.getLogger(__name__)


class ConnectorMQTTIntegration():
    """
    This class allows the API (django) to communicate with the connectors via
    MQTT. 
    
    It has some mechanisms implemented to ensure that only one instance of this 
    class is running, to prevent concurrent and redundand read/write operations
    the djangos DB.

    Within the admin_interface app this class will be instantiated in apps.py.
    Parts of the class will be called at runtime to react on changed settings
    from within signals.py.
    """
    
    def __new__(cls, *args, **kwargs):
        """
        Ensure singleton, i.e. only one instance is created.
        """
        if not hasattr(cls, "_instance"):
            # This magically calls __init__ with the correct arguements too.
            cls._instance = object.__new__(cls)
        else:
            logger.warning(
                "ConnectorMQTTIntegration is aldready running. Use "
                "get_instance method to retrieve the running instance."
            )
        return cls._instance

    def __init__(self, mqtt_client=Client):
        """
        Initial configuration of the MQTT communication.
        """
        
        # Ignore the potentially changed configuration if instance, and thus
        # also an MQTT client, exist.
        # If a new configuration should be used, disconnect and destroy the 
        # current instance and create a new one.
        if hasattr(self, "client"):
            return
        
        # Below the normal startup and configration of this class.
        logger.info("Starting up Connector MQTT Integration.")

        # The configuration for connecting to the broker.
        connect_kwargs = {
            'host': settings.MQTT_BROKER['host'],
            'port': settings.MQTT_BROKER['port'],
        }

        # The private userdata, used by the callbacks.
        userdata = {
            'models': models,
            'connect_kwargs': connect_kwargs,
            'topics': {},
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        # Fill the topics within userdata
        self.update_topics()

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        # Start loop in background process.
        self.client.loop_start()

        # Subscripe to all computed topics.
        self.update_subscriptions()

    @classmethod
    def get_instance(cls):
        """
        Return the running instance of the class.
        
        Returns:
        --------
        instance: ConnectorMQTTIntegration instance
            The running instance of the class. Is none of not running yet.
        """
        if hasattr(cls, "_instance"):
            instance = cls._instance
        else:
            instance = None
        return instance

    def disconnect(self):
        """
        Shutdown gracefully -> Disconnect from broker and stop background loop.
        """
        self.client.disconnect()
        self.client.loop_stop()

    def update_topics(self):
        """
        Computes a list of all topics associated with the currently
        registered Connecetors. Places this list in the relevant places.

        Returns nothing. The stored topics object looks like this:
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
        
        # It might be more efficient to extract the topics only for those
        # connectors which have been edited. However, at the time of 
        # implementation the additional effort did not seem worth it.
        for connector in models.Connector.objects.all():
            for message_type in message_types:
                topic = getattr(connector, message_type)
                topics[topic] = (connector, message_type)
                
        # Store the topics and update the client userdata, so the callbacks
        # will have up to date data.
        self.userdata['topics'] = topics
        self.client.user_data_set(self.userdata)

    def update_subscriptions(self):
        """
        Updates subscriptions.
        
        Should be used if the topics object has changed, i.e. call directly 
        after self.update_topics().
        """
        topics = self.userdata['topics']
        
        # Start with no subscription on first run.
        if not hasattr(self, "connected_topics"):
            self.connected_topics  = []
        
        # Subsribe to topics not subscribed yet.
        for topic in topics:
            if topic not in self.connected_topics:
                # use QOS=2, expect messages once and only once.
                # No duplicates in log files etc.
                self.client.subscribe(topic=topic, qos=2)
                self.connected_topics.append(topic)
        
        # Unsubscribe from topics no longer relevant.
        for topic in self.connected_topics:
            if topic not in topics:
                self.client.unsubscribe(topic=topic)

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
                    # TODO: only test version below -> create with correct device and unit
                    if not models.Datapoint.objects.filter(datapoint_key_in_connector=key).exists():
                        try:
                            _ = models.Datapoint(
                                datapoint_key_in_connector=key,
                            ).save()
                        except Exception:
                            logger.exception(
                                'Exception while writing datapoint into DB.'
                            )

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
