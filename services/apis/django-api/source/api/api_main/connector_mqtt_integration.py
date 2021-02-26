import json
import logging
from time import sleep
from threading import Thread, Lock, Event

from django.conf import settings
from django.db import IntegrityError
from paho.mqtt.client import Client
from cachetools.func import ttl_cache

from .models.datapoint import Datapoint, DatapointValue
from .models.datapoint import DatapointSetpoint, DatapointSchedule
from .models.connector import Connector, ConnectorHeartbeat, ConnectorLogEntry
from .models.controller import Controller, ControlledDatapoint
from ems_utils.timestamp import datetime_from_timestamp

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

    def __init__(self, mqtt_client=Client, n_cmi_write_threads_overload=None):
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
        logger.info(
            "Starting up Connector MQTT Integration. This includes connecting "
            "to the required topics and processing the retained messages. "
            "This might take a few minutes."
        )

        # The configuration for connecting to the broker.
        connect_kwargs = {
            'host': settings.MQTT_BROKER['host'],
            'port': settings.MQTT_BROKER['port'],
        }

        # Get this from settings in future:
        self.HISTORY_DB = True
        self.N_CMI_WRITE_THREADS = 32 # This should be 1 for SQLite
        if n_cmi_write_threads_overload is not None:
            self.N_CMI_WRITE_THREADS = n_cmi_write_threads_overload

        # Locks and queue for the message_handle_worker threads.
        self.message_queue = []
        self.message_queue_lock = Lock()
        self.get_datapoint_by_id_lock = Lock()
        self.shutdown_event = Event()

        # Start the threads that handle the incomming messages.
        # Note that (at least for ./manage.py runserver) there exists
        # no clean shutdown protocol. Triggering the keyboard interupt
        # will just kill Django hard and the Django main thread is set
        # up as a daemon to be killed by the OS as this seems to be faster.
        # Hence we have no change in this program to rely on a graceful
        # shutdown and start our threads as deamons too.
        self.msg_handler_threads = []
        for i in range(self.N_CMI_WRITE_THREADS):
            message_handler_thread = Thread(
                target=self.message_handle_worker, args=(), daemon=True,
            )
            message_handler_thread.start()
            self.msg_handler_threads.append(message_handler_thread)

        # The private userdata, used by the callbacks.
        userdata = {
            'connect_kwargs': connect_kwargs,
            'message_queue': self.message_queue,
            'message_queue_lock': self.message_queue_lock,
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_unsubscribe = self.on_unsubscribe

        # Fill the topics within userdata
        self.update_topics()

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        # Start loop in background process.
        self.client.loop_start()

        # Subscripe to all computed topics.
        self.update_subscriptions()

        # Republish the last known state of datapoint_maps and
        # controlled datapoints, in case they haven't been retained by the
        # broker, e.g. after a CD run with an existing database.
        self.create_and_send_datapoint_map()
        self.create_and_send_controlled_datapoints()

        logger.debug("Init of Connector MQTT Integration completed.")


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
        Shutdown gracefully.

        Disconnect from broker, stop background loop and join threads.
        """
        self.client.disconnect()
        self.client.loop_stop()
        # Remove the client, so init can establish a new connection.
        del self.client

        # Tell all worker threads to stop.
        self.shutdown_event.set()
        for thread in self.msg_handler_threads:
            thread.join()

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
        logger.debug("Entering update_topics method")

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
            active_datapoints = datapoint_set.filter(is_active=True)
            for active_datapoint in active_datapoints:
                datapoint_topics = active_datapoint.get_mqtt_topics()
                for datapoint_msg_type in datapoint_topics:
                    datapoint_topic = datapoint_topics[datapoint_msg_type]
                    topics[datapoint_topic] = (
                        connector,
                        "mqtt_topic_datapoint_%s_message" % datapoint_msg_type,
                    )

        self.topics = topics

        logger.debug("Leaving update_topics method")

    def update_subscriptions(self):
        """
        Updates subscriptions.

        Should be used if the topics object has changed, i.e. call directly
        after self.update_topics().
        """
        logger.debug("Entering update_subscriptions method")

        topics = self.topics

        # Start with no subscription on first run.
        if not hasattr(self, "connected_topics"):
            self.connected_topics = []

        # Subsribe to topics not subscribed yet.
        for topic in topics:
            if topic not in self.connected_topics:
                # use QOS=2, expect messages once and only once.
                # No duplicates in log files etc.
                result, mid = self.client.subscribe(topic=topic, qos=2)
                logger.info(
                    "Subscribing (%s) to topic %s with status: %s",
                    *(mid, topic, result)
                )
                self.connected_topics.append(topic)

        # Unsubscribe from topics no longer relevant.
        connected_topics_update = []
        for topic in self.connected_topics:
            if topic not in topics:
                result, mid = self.client.unsubscribe(topic=topic)
                logger.info(
                    "Unsubscribing (%s) from topic %s with status: %s",
                    *(mid, topic, result)
                )
            else:
                connected_topics_update.append(topic)
        self.connected_topics = connected_topics_update

        logger.debug("Leaving update_subscriptions method")

    def create_and_send_datapoint_map(self, connector=None):
        """
        Creates and sends a datapoint_map.

        Arguments:
        ----------
        connector: Connector object or None.
            If not None compute only the datapoint_map for the specified
            connector. Else will process all connectors.
        """
        logger.debug("Entering create_and_send_datapoint_map method")

        if connector is None:
            connectors = Connector.objects.all()
        else:
            connectors = [connector]

        for connector in connectors:
            # This is the minimal viable datapoint map accepted by the
            # Connectors.
            datapoint_map = {"sensor": {}, "actuator": {}}
            datapoints = connector.datapoint_set
            active_datapoints = datapoints.filter(is_active=True)

            # Create the map entry for every used datapoint
            for active_datapoint in active_datapoints:

                _type = active_datapoint.type
                key_in_connector = active_datapoint.key_in_connector
                mqtt_topic = active_datapoint.get_mqtt_topics()["value"]
                if _type == "sensor":
                    datapoint_map[_type][key_in_connector] = mqtt_topic
                elif _type == "actuator":
                    datapoint_map[_type][mqtt_topic] = key_in_connector

            # Send the final datapoint_map to the connector.
            # Use qos=2 to ensure the message is received by the connector.
            payload = json.dumps(datapoint_map)
            topic = connector.mqtt_topic_datapoint_map
            self.client.publish(
                topic=topic,
                payload=payload,
                qos=2,
                retain=True
            )

            logger.debug("Leaving create_and_send_datapoint_map method")

    def create_and_send_controlled_datapoints(self, controller=None):
        """
        Computes and sends a list of controlled datapoints to a connector.
        """
        logger.debug("Entering create_and_send_controlled_datapoints method")

        if controller is None:
            controllers = Controller.objects.all()
        else:
            controllers = [controller]

        for controller in controllers:
            controlled_datapoints = ControlledDatapoint.objects.filter(
                controller=controller
            )
            controlled_datapoint_msgs = []
            for cd in controlled_datapoints:
                # Get the topics of the datapoints.
                sensor_topics = cd.sensor_datapoint.get_mqtt_topics()
                sensor_value_topic = sensor_topics["value"]
                actuator_topics = cd.actuator_datapoint.get_mqtt_topics()
                actuator_value_topic = actuator_topics["value"]
                actuator_setpoint_topic = actuator_topics["setpoint"]
                actuator_schedule_topic = actuator_topics["schedule"]

                # Build the message for this controlled datapoint object.
                controlled_datapoints_msg = {
                    "sensor": {
                        "value": sensor_value_topic,
                    },
                    "actuator": {
                        "value": actuator_value_topic,
                        "setpoint": actuator_setpoint_topic,
                        "schedule": actuator_schedule_topic,
                    }
                }
                controlled_datapoint_msgs.append(controlled_datapoints_msg)

            # Publish the msg to the controller.
            self.client.publish(
                topic=controller.mqtt_topic_controlled_datapoints,
                payload=json.dumps(controlled_datapoint_msgs),
                qos=2,
                retain=True
            )

            logger.debug(
                "Leaving create_and_send_controlled_datapoints method"
            )

    @staticmethod
    def on_message(client, userdata, msg):
        """
        Handles incoming messages by storing them into the queue.

        This method must return fast as long waiting times will result in
        dropped MQTT messages. Hence we just put into a queue here and return.

        Arguments:
        ----------
        See paho mqtt documentation.
        """
        logger.debug("on_message received msg with topic %s" % msg.topic)
        if msg is None:
            # Don't store message with no content to prevent slowing down
            # the message_handle_worker
            return

        # Save the message in the queue for the message_handle_worker threads.
        # Check first that the threads have a chance of getting rid of the
        # messages and drop the message if not to prevent unlimted growth of
        # the queue. Testing with PostgreSQL DB on a small VM we were able
        # to process 400 messages/s. Hence a limit of 10000 messages
        # corresponds to a delay of roughly 25 seconds between the time
        # the message way received from MQTT and the time it is written to
        # DB.
        with userdata["message_queue_lock"]:
            if len(userdata["message_queue"]) < 10000:
                userdata["message_queue"].append(msg)
            else:
                logger.warning(
                    "Message Queue full! Droping message with topic: %s"
                    % msg.topic
                )

    @ttl_cache(maxsize=None, ttl=15*60)
    def get_datapoint_by_id(self, id):
        """
        This is a simple wrapper that acts as a cache.

        The ttl ensures that we refreash every 15 Minutes from the DB.
        """
        return Datapoint.objects.get(id=id)

    def message_handle_worker(self):
        """
        Handle queued mqtt messages by writing to appropriate DB tables.

        Revise the message_format definition within the repo's documentation
        folder for more information on the structure of the incoming messages.

        TODO: Streamline performance for logs, heartbeats and
              available_datapoint messages.
        """
        while True:
            # Check if the the program is going to stop and terminate if yes.
            if self.shutdown_event.isSet():
                return

            # Try to fetch a message from the queue.
            with self.message_queue_lock:
                if self.message_queue:
                    msg = self.message_queue.pop(0)
                    logger.debug(
                        "Current message queue length is: %s"
                        % len(self.message_queue)
                    )
                else:
                    msg = None

            # Wait a bit if the the queue was empty and retry.
            if msg is None:
                sleep(0.05)
                continue

            logger.debug(
                "message_handle_worker processing msg with topic %s"
                % msg.topic
            )
            topics = self.topics

            connector, message_type = topics[msg.topic]
            payload = json.loads(msg.payload)
            if message_type == "mqtt_topic_datapoint_value_message":
                # If this message has reached that point, i.e. has had a
                # topic entry it means that the Datapoint object must exist, as
                # else the MQTT topic could not have been computed.
                try:
                    # The datapoint id is encoded into the MQTT topic.
                    # Check the datapoint definiton.
                    datapoint_id = msg.topic.split("/")[-2]
                    # Cachetools are not thread safe and recommend using a lock
                    with self.get_datapoint_by_id_lock:
                        datapoint = self.get_datapoint_by_id(id=datapoint_id)
                    timestamp = datetime_from_timestamp(payload["timestamp"])
                    # Value/Setpoint/Schedule Messages will be new objects
                    # in most cases. That a message with the same datapoint
                    # and timestamp exists already in the DB is rather a
                    # special case if we retained an old message from the
                    # broker, or if developing with ./manage.py runserver
                    # without the --noreload flag.
                    # Hence, to increase performance, we just try to create
                    # the new entry as this removes the burden to fetch the
                    # object first. Only if this fails we perform an update.
                    # Also only do this if the Admin requested that the
                    # history is preserved.
                    if self.HISTORY_DB:
                        try:
                            DatapointValue(
                                datapoint=datapoint,
                                timestamp=timestamp,
                                value=payload["value"],
                            ).save()
                        except IntegrityError:
                            dp_value = DatapointValue.objects.get(
                                datapoint=datapoint,
                                timestamp=timestamp,
                            )
                            dp_value.value = payload["value"]
                            dp_value.save()
                            logger.info(
                                "Overwrote existing datapoint value msg for "
                                "datapoint with id %s and timestamp %s"
                                % (datapoint.id, timestamp)
                            )
                    # Once we stored the value also check if this value
                    # is the most recent one and if so update the
                    # corresponding fields of Datapoint too.
                    existing_ts = datapoint.last_value_timestamp
                    if existing_ts is None or existing_ts <= timestamp:
                        datapoint.last_value = payload["value"]
                        datapoint.last_value_timestamp = timestamp
                        datapoint.save(
                            update_fields=[
                                "last_value",
                                "last_value_timestamp",
                            ]
                        )
                except Exception:
                    logger.exception(
                        'Exception while writing datapoint value to DB.\n'
                        'The topic was: %s' % msg.topic
                    )

            elif message_type == "mqtt_topic_datapoint_schedule_message":
                # see comments of handling of datapoint_value_message above.
                try:
                    datapoint_id = msg.topic.split("/")[-2]
                    with self.get_datapoint_by_id_lock:
                        datapoint = self.get_datapoint_by_id(id=datapoint_id)
                    timestamp = datetime_from_timestamp(payload["timestamp"])
                    if self.HISTORY_DB:
                        try:
                            DatapointSchedule(
                                datapoint=datapoint,
                                timestamp=timestamp,
                                schedule=payload["schedule"],
                            ).save()
                        except IntegrityError:
                            dp_schedule = DatapointSchedule.objects.get(
                                datapoint=datapoint,
                                timestamp=timestamp,
                            )
                            dp_schedule.schedule = payload["schedule"]
                            dp_schedule.save()
                            logger.info(
                                "Overwrote existing datapoint schedule msg for "
                                "datapoint with id %s and timestamp %s"
                                % (datapoint.id, timestamp)
                            )
                    existing_ts = datapoint.last_schedule_timestamp
                    if existing_ts is None or existing_ts <= timestamp:
                        datapoint.last_schedule = payload["schedule"]
                        datapoint.last_schedule_timestamp = timestamp
                        datapoint.save(
                            update_fields=[
                                "last_schedule",
                                "last_schedule_timestamp",
                            ]
                        )
                except Exception:
                    logger.exception(
                        'Exception while writing datapoint schedule to DB.\n'
                        'The topic was: %s' % msg.topic
                    )

            elif message_type == "mqtt_topic_datapoint_setpoint_message":
                # see comments of handling of datapoint_value_message above.
                try:
                    datapoint_id = msg.topic.split("/")[-2]
                    with self.get_datapoint_by_id_lock:
                        datapoint = self.get_datapoint_by_id(id=datapoint_id)
                    timestamp = datetime_from_timestamp(payload["timestamp"])
                    if self.HISTORY_DB:
                        try:
                            DatapointSetpoint(
                                datapoint=datapoint,
                                timestamp=timestamp,
                                setpoint=payload["setpoint"],
                            ).save()
                        except IntegrityError:
                            dp_setpoint = DatapointSetpoint.objects.get(
                                datapoint=datapoint,
                                timestamp=timestamp,
                            )
                            dp_setpoint.setpoint = payload["setpoint"]
                            dp_setpoint.save()
                            logger.info(
                                "Overwrote existing datapoint setpoint msg for "
                                "datapoint with id %s and timestamp %s"
                                % (datapoint.id, timestamp)
                            )
                    existing_ts = datapoint.last_setpoint_timestamp
                    if existing_ts is None or existing_ts <= timestamp:
                        datapoint.last_setpoint = payload["setpoint"]
                        datapoint.last_setpoint_timestamp = timestamp
                        datapoint.save(
                            update_fields=[
                                "last_setpoint",
                                "last_setpoint_timestamp",
                            ]
                        )
                except Exception:
                    logger.exception(
                        'Exception while writing datapoint setpoint to DB.\n'
                        'The topic was: %s' % msg.topic
                    )

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
                    logger.exception(
                        'Exception while writing Log into DB.\n'
                        'The topic was: %s' % msg.topic
                    )

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
                    logger.exception(
                        'Exception while writing heartbeat into DB.\n'
                        'The topic was: %s' % msg.topic
                    )

            elif message_type == 'mqtt_topic_available_datapoints':
                for datapoint_type in payload:
                    for key, example in payload[datapoint_type].items():

                        if not Datapoint.objects.filter(
                                # Handling if the Datapoint does not exist yet.
                                connector=connector,
                                key_in_connector=key,
                                type=datapoint_type).exists():
                            try:
                                _ = Datapoint(
                                    connector=connector,
                                    type=datapoint_type,
                                    key_in_connector=key,
                                    example_value=example,
                                ).save()
                            except Exception:
                                logger.exception(
                                    'Exception while writing available '
                                    'datapoint into DB.\n'
                                    'The topic was: %s' % msg.topic
                                )

                        else:
                            # Update existing datapoint. If we reach this
                            # point it means that nothing of the datapoint can
                            # have changed from the example value. Thus we trigger
                            # an update of the example value to present the
                            # possible more recent information to the admin.
                            try:
                                datapoint = Datapoint.objects.get(
                                    connector=connector,
                                    key_in_connector=key,
                                    type=datapoint_type
                                )
                                if datapoint.example_value != example:
                                    datapoint.example_value = example
                                    datapoint.save(
                                        # This prevents that the datapoint_map is
                                        # updated.
                                        update_fields=[
                                            "example_value",
                                        ]
                                    )
                            except Exception:
                                logger.exception(
                                    'Exception while updating available '
                                    'datapoint.'
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

    @staticmethod
    def on_subscribe(client, userdata, mid, granted_qos):
        logger.debug('Subscribe successful: %s, %s', mid, granted_qos)

    @staticmethod
    def on_unsubscribe(client, userdata, mid):
        logger.debug('Unsubscribe successful: %s', mid)
        # TODO: Set subscription status of av. datapoint here?
