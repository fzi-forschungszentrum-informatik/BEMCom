import json
import logging

from paho.mqtt.client import Client
from django.conf import settings

from .utils import datetime_from_timestamp
from .models.datapoint import Datapoint
from .models.connector import Connector, ConnectorHeartbeat, ConnectorLogEntry

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

        # Don't subscribe to the datapoint_message_wildcard topic, we want to
        # control which messages we receive, in order to prevent the case
        # were incoming messages from a wildcard topic have no corresponding
        # equivalent in the database and cause errors.
        message_types = [
            'mqtt_topic_logs',
            'mqtt_topic_heartbeat',
            'mqtt_topic_available_datapoints',
        ]

        # It might be more efficient to extract the topics only for those
        # connectors which have been edited. However, at the time of
        # implementation the additional effort did not seem worth it.
        for connector in Connector.objects.all():
            for message_type in message_types:
                topic = getattr(connector, message_type)
                topics[topic] = (connector, message_type)

            # Also store the topics of the used datapoints.
            datapoint_set = connector.datapoint_set
            used_datapoints = datapoint_set.exclude(use_as="not used")
            for used_datapoint in used_datapoints:
                datapoint_topic = used_datapoint.get_mqtt_topic()
                topics[datapoint_topic] = (
                    connector,
                    "mqtt_topic_datapoint_message",
                )

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
            self.connected_topics = []

        # Subsribe to topics not subscribed yet.
        for topic in topics:
            if topic not in self.connected_topics:
                # use QOS=2, expect messages once and only once.
                # No duplicates in log files etc.
                self.client.subscribe(topic=topic, qos=2)
                self.connected_topics.append(topic)

        # Unsubscribe from topics no longer relevant.
        connected_topics_update = []
        for topic in self.connected_topics:
            if topic not in topics:
                self.client.unsubscribe(topic=topic)
            else:
                connected_topics_update.append(topic)
        self.connected_topics = connected_topics_update

    def create_and_send_datapoint_map(self, connector=None):
        """
        Creates and sends a datapoint_map.

        Arguments:
        ----------
        connector: Connector object or None.
            If not None compute only the datapoint_map for the specified
            connector. Else will process all connectors.
        """
        if connector is None:
            connectors = Connector.objects.all()
        else:
            connectors = [connector]

        for connector in connectors:
            # This is the minimal viable datapoint map accepted by the
            # Connectors.
            datapoint_map = {"sensor": {}, "actuator": {}}
            datapoints = connector.datapoint_set
            used_datapoints = datapoints.exclude(use_as="not used")

            # Create the map entry for every used datapoint
            for used_datapoint in used_datapoints:

                _type = used_datapoint.type
                key_in_connector = used_datapoint.key_in_connector
                mqtt_topic = used_datapoint.get_mqtt_topic()

                if used_datapoint.type not in datapoint_map:
                    datapoint_map[used_datapoint.type] = {}
                datapoint_map[_type][key_in_connector] = mqtt_topic

            # Send the final datapoint_map to the connector.
            # Use qos=2 to ensure the message is received by the connector.
            payload = json.dumps(datapoint_map)
            topic = connector.mqtt_topic_datapoint_map
            self.client.publish(
                topic=topic,
                payload=payload,
                qos=2,
            )

    @staticmethod
    def on_message(client, userdata, msg):
        """
        Handle incomming mqtt messages by writing to appropriate DB tables.

        Revise the message_format definition within the repo's documentation
        folder for more information on the structure of the incoming messages.

        Arguments:
        ----------
        See paho mqtt documentation.
        """
        topics = userdata['topics']

        connector, message_type = topics[msg.topic]
        payload = json.loads(msg.payload)
        if message_type == "mqtt_topic_datapoint_message":
            # If this message has reached that point, i.e. has had a
            # topic entry it means that the Datapoint object must exist, as
            # else the MQTT topic coulc not habe been computed.
            try:
                # TODO Remove this.
                logger.error('Got Message on topic: {}\nWith payload\n{}'.format(msg.topic, msg.payload))
                # Make use of the convention that the Datapoint topic ends
                # with the primary key of the Datapoint.
                datapoint_id = msg.topic.split("/")[-1]
                datapoint = Datapoint.objects.get(id=datapoint_id)

                # Get the object of the Datapoint's DatapointAddition and
                # update it with the currenttly received timestamp and value.
                addition_object = datapoint.get_addition_object()
                addition_object.last_value = payload["value"]
                addition_object.last_timestamp = datetime_from_timestamp(
                    payload["timestamp"]
                )
                addition_object.save()
            except Exception:
                logger.exception(
                    'Exception while updating datapoint_message in DB.'
                )
                # This raise will be caught by paho mqtt. It should not though.
                raise
        elif message_type == 'mqtt_topic_logs':
            timestamp = datetime_from_timestamp(payload['timestamp'])
            try:
                _ = ConnectorLogEntry(
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

        elif message_type == 'mqtt_topic_heartbeat':
            try:
                hb_model = ConnectorHeartbeat
                # Create a new DB entry if this is the first time we see a
                # heartbeat message for this connector. This code prevents
                # creating an object with invalid values for the heartbeat
                # entries (i.e. null or 1.1.1970, etc.) which should be
                # beneficial for downstream code that relies on valid entries.
                if not hb_model.objects.filter(connector=connector).exists():
                    _ = hb_model(
                        connector=connector,
                        last_heartbeat=datetime_from_timestamp(
                            payload['this_heartbeats_timestamp']
                        ),
                        next_heartbeat=datetime_from_timestamp(
                            payload['next_heartbeats_timestamp']
                        ),
                    ).save()
                # Else this is an update to an existing entry. There should
                # be only one heartbeat entry per connector, enforced by the
                # unique constraint of the connector field.
                else:
                    hb_object = hb_model.objects.get(connector=connector)
                    hb_object.last_heartbeat = datetime_from_timestamp(
                        payload['this_heartbeats_timestamp']
                    )
                    hb_object.next_heartbeat = datetime_from_timestamp(
                        payload['next_heartbeats_timestamp']
                    )
                    hb_object.save()
            except Exception:
                logger.exception('Exception while writing heartbeat into DB.')
                # This raise will be caught by paho mqtt. It should not though.
                raise

        elif message_type == 'mqtt_topic_available_datapoints':
            for datapoint_type in payload:
                for key, example in payload[datapoint_type].items():

                    if not Datapoint.objects.filter(
                            # Handling if the Datapoint does not exist yet.
                            connector=connector,
                            key_in_connector=key).exists():
                        try:
                            _ = Datapoint(
                                connector=connector,
                                type=datapoint_type,
                                key_in_connector=key,
                                example_value=example,
                            ).save()
                        except Exception:
                            logger.exception(
                                'Exception while writing available datapoint '
                                'into DB.'
                            )
                            # This raise will be caught by paho mqtt.
                            # It should not though.
                            raise

                    else:
                        # Update existing datapoint.
                        try:
                            datapoint = Datapoint.objects.get(
                                connector=connector,
                                key_in_connector=key
                            )
                            datapoint.type = datapoint_type
                            datapoint.example_value = example
                            datapoint.save()
                        except Exception:
                            logger.exception(
                                'Exception while updating available datapoint.'
                            )
                            # This raise will be caught by paho mqtt.
                            # It should not though.
                            raise

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
