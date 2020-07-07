# -*- coding: utf-8 -*-
"""
This is the controller. See the Readme.md files for details.
"""
import os
import sys
import json
import logging
from threading import Timer
from datetime import datetime


from dotenv import load_dotenv, find_dotenv
from paho.mqtt.client import Client

logger = logging.getLogger(__name__)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=log_format)

def timestamp_now():
    """
    Computes the current timestamp in ms since epoch (UTC).
    """
    dt_utcnow = datetime.utcnow()
    ts_seconds = datetime.timestamp(dt_utcnow)
    return round(ts_seconds * 1000)


def sort_schedule_setpoint_items(items):
    """
    This can be used to sort the items of schedule/setpoint.

    The ordering is especially relevant if items overlap, which should not
    exist though. But if it does, the following ensures that in case of
    overlap we start with the first item and switch to the second once the
    time of the second has come. If items have from_timestamp = None, then
    they will be executed at the very beginning, as everything with a specified
    from_timestamp is certainly thought to start later. If multiple items exist
    for which from_timestamp is None we take care that an item that has also
    to_timestamp = None is the last of the ones with from_timestamp = None, as
    we exepct that this item is then ment to be executed.
    """
    def sort_key(item):
        """
        Inspred by:
        https://stackoverflow.com/questions/18411560/python-sort-list-with-none-at-the-end
        """
        return (
            item["from_timestamp"] is not None,
            item["to_timestamp"] is None,
            item["from_timestamp"]
        )
    return sorted(items, key=sort_key)


class Controller():

    def __init__(self, mqtt_broker_host, mqtt_broker_port, mqtt_config_topic,
                 mqtt_client=Client, timestamp_now=timestamp_now):
        """
        Arguments:
        ----------
        mqtt_broker_host: str
            The URL of the MQTT Broker. See Readme.md for details.
        mqtt_broker_port: str
            The port of the MQTT Broker. See Readme.md for details.
        mqtt_config_topic: str
            The topic on which the controller listens for the config object.
            See Readme.md for details.
        mqtt_client: object
            The client object of the MQTT lib. Allows using fake mqtt client
            while running tests.
        timestamp_now: function
            The function used to compute the current timestamp. Should only be
            overloaded for tests.
        """
        # Below the normal startup and configration of this class.
        logger.info("Starting up Controller.")

        # The configuration for connecting to the broker.
        connect_kwargs = {
            "host": mqtt_broker_host,
            "port": int(mqtt_broker_port),
        }

        self.config_topic = mqtt_config_topic
        self.timestamp_now = timestamp_now

        self.topic_index = {}
        self.topics_per_id = {}
        self.timers_per_topic = {}
        self.current_values = {}

        # The private userdata, used by the callbacks.
        userdata = {
            "connect_kwargs": connect_kwargs,
            "self": self,
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Initial connection to broker.
        self.client.connect(**connect_kwargs)

        self.client.subscribe(mqtt_config_topic)
        logger.info("Using topic for configuration: %s", mqtt_config_topic)

        # Start loop in background process.
        self.client.loop_forever()

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
        """
        Handle incomming messages.

        For config messages:
            Updates to topics that the controller is subscribed to.

        For value messages:
            Just stores the message, as values are valid immideatly.

        For setpoint/schedule messages:
            Parses the schedule/setpoint items and adds a timer that will
            push the content of the item to the currently active block once the
            timer is over.
        """
        # This try/except is necessary as Paho MQTT silently drops all
        # exceptions, so we at least write them into the logs.
        try:
            self = userdata["self"]
            if msg.topic == self.config_topic:
                logger.info("Received new configuration message")
                payload = json.loads(msg.payload)

                # Build up a topic index, linking from the topic to the topic
                # of the corresponding sensor value, the later is thereby used
                # as an id under which the last messages are stored.
                topic_index_new = {}
                for control_group in payload:

                    sensor_value_topic = control_group["sensor"]["value"]
                    actu_setpoint_topic = control_group["actuator"]["setpoint"]
                    actu_schedule_topic = control_group["actuator"]["schedule"]

                    topic_index_new[sensor_value_topic] = {
                        "id": sensor_value_topic,
                        "type": "sensor_value",
                    }
                    topic_index_new[actu_setpoint_topic] = {
                        "id": sensor_value_topic,
                        "type": "actuator_setpoint",
                    }
                    topic_index_new[actu_schedule_topic] = {
                        "id": sensor_value_topic,
                        "type": "actuator_schedule",
                    }

                # Now use the index and the previous versionf of it to
                # subscribe to all topics for that are new in the last message
                # and unsubscribe from all topics that are no longer in the
                # config.
                topic_index_old = self.topic_index
                new_topics = topic_index_new.keys() - topic_index_old.keys()
                rm_topics = topic_index_old.keys() - topic_index_new.keys()
                self.topic_index = topic_index_new
                for topic in new_topics:
                    client.subscribe(topic, 0)
                    logger.info("Subscribed to topic: %s", topic)
                for topic in rm_topics:
                    client.unsubscribe(topic)
                    logger.info("Unsubscribed from topic: %s", topic)

                    # Also delete all timers for the topics, as we expect that
                    # it is not controlled anymore.
                    self.cancel_timers(topic)

                # Finally also add the topics to a dict that allows looking
                # up the topics given the sensor_value_id. Don't delete old
                # topics here as we should not receive any schedules/setpoints
                # for them in future, but some timers might still be running.
                for control_group in payload:
                    sensor_value_topic = control_group["sensor"]["value"]
                    self.topics_per_id[sensor_value_topic] = control_group
                return

            # Now the handling for the normal messages.
            topic_index = self.topic_index

            # First check if any timers exist that have been created from the
            # previous data. If so deactivate all of those.
            self.cancel_timers(msg.topic)

            # Now start handling the new data.
            _id = topic_index[msg.topic]["id"]
            _type = topic_index[msg.topic]["type"]

            # Sensor values are applied immediately.
            if _type == "sensor_value":
                self.update_current_value(
                    _id=_id,
                    _type=_type,
                    payload=json.loads(msg.payload)["value"]
                )
                return
            # For setpoints and schedules the items are paresed and new timers
            # are created that store the corresponding values to current values
            # once their time has come.
            if _type == "actuator_setpoint":
                items = json.loads(msg.payload)["setpoint"]
            if _type == "actuator_schedule":
                items = json.loads(msg.payload)["schedule"]

            # The order of items matters, at least for overlapping items.
            # Hence sort the items, see the docstring of the sort function for
            # details
            items = sort_schedule_setpoint_items(items)

            for item in items:
                # fix the current timestamp to prevent any issues where e.g.
                # from_timestamp would have been in the future while checking
                # for the first time, but not on the second time.
                timestamp_now = self.timestamp_now()

                from_timestamp = item["from_timestamp"]
                to_timestamp = item["to_timestamp"]
                # Ignore items that are passed already.
                if to_timestamp is not None and to_timestamp <= timestamp_now:
                    continue
                # if from_timestamp now is None (convention for execute ASAP)
                # or in the past, exectue immediately
                if (from_timestamp is None or from_timestamp <= timestamp_now):
                    self.update_current_value(
                        _id=_id,
                        _type=_type,
                        payload=item
                    )
                # from_timestamp is in the future
                else:
                    # Start up a timer instance that delays the call to
                    # update_current_value until the time has come.
                    # Also store the timer object so we can cancel it if new
                    # data arrives.
                    delay_ms = (from_timestamp - timestamp_now)
                    delay_s = delay_ms / 1000.
                    timer_kwargs = {
                        "_id": _id,
                        "_type": _type,
                        "payload": item,
                    }
                    timer = Timer(
                        interval=delay_s,
                        function=self.update_current_value,
                        kwargs=timer_kwargs
                    )
                    timer.start()
                    self.add_timer(msg.topic, timer)
                # to_timstamp = None means by convention execute forever, thus
                # no timer necessary in this case.
                if to_timestamp is None:
                    continue

                # If another item starts directly after this one or would start
                # before the current item is finsihed we can ignore
                # the to_timestamp time. Consider here that items are sorted.
                i = items.index(item)
                ignore_to_timesamp = False
                for following_item in items[i:]:
                    if (following_item["from_timestamp"] is None or
                            following_item["from_timestamp"] <= to_timestamp):
                        ignore_to_timesamp = True
                        break
                if ignore_to_timesamp:
                    continue

                # For the remaining case, i.e. no overlapping item and not
                # directly aligned item, we implement the default strategy to
                # preserve energy. That is we define the setpoint such that
                # preferred_value is None (i.e. devie off), and remove any
                # contraints for the optimizer. If no schedule is defined, we
                # implement similary that the device should be turned off
                # if the setpoint allows it.
                if _type == "actuator_setpoint":
                    kwargs = {
                        "preferred_value": None,
                        "acceptable_values": None,
                        "min_value": None,
                        "max_value": None,
                    }
                elif _type == "actuator_schedule":
                    kwargs = {
                        "value": None
                    }
                delay_ms = (to_timestamp - timestamp_now)
                delay_s = delay_ms / 1000.
                timer = Timer(
                    interval=delay_s,
                    function=self.update_current_value,
                    kwargs=kwargs
                )

        except Exception:
            logger.exception(
                "Expection while processing MQTT message.\n"
                "Topic: %s\n"
                "Message:\n%s",
                *(msg.topic, msg.payload)
            )
            raise

    def disconnect(self):
        """
        Shutdown gracefully -> Disconnect from broker and stop background loop.
        """
        self.client.disconnect()
        self.client.loop_stop()
        # Remove the client, so init can establish a new connection.
        del self.client

    def update_current_value(self, _id, _type, payload):
        """
        Stores the value message or schedule/setpoint item that is currently
        active. Also call the update_actuator_value method, as this function
        is often called from a timer.

        Arguments:
        ----------
        _id: string
            The id (i.e. mqtt topic for the sensor values
        _type: string
            The type of the incomming message, one of: sensor_value,
            actuator_setpoint and actuator_schedule.
        payload: dict
            all the content of msg.payload

        TODO: Maybe ensure that the current values are not overwritten by
              older messages, e.g. replays.
        """
        if _id not in self.current_values:
            self.current_values[_id] = {}
        self.current_values[_id][_type] = payload
        self.update_actuator_value(_id)

    def update_actuator_value(self, _id):
        """
        Computes and sends a value msg to an actuator datapoint.

        This function is called every time something changes, e.g. a new sensor
        value has arrived, or the current setpoint or schedule values have
        changed. It computes the corresponding actuator value and sends it
        if it has changed.

        Arguments:
        ----------
        _id: string
            The id (i.e. mqtt topic for the sensor values
        """
        actuator_value_topic = self.topics_per_id[_id]["actuator"]["value"]
        current_sensor_value = None
        current_schedule = None
        current_setpoint = None
        # acceptable_values may be set to None, which indicates any value for
        # the sensor datapoint is acceptable. The bool variable is thus
        # required to distinguish the case when acceptable_values is not given
        # in message, vs. when it's explicitly set to None.
        discrete_flexibility = False
        current_acceptable_values = None
        # Similar to acceptable values but for the continuous case.
        continuous_flexibilty = False
        current_min_value = None
        current_max_value = None

        if "sensor_value" in self.current_values[_id]:
            current_sensor_value = self.current_values[_id]["sensor_value"]
        if "actuator_schedule" in self.current_values[_id]:
            current_schedule = self.current_values[_id]["actuator_schedule"]
            schedule_value = current_schedule["value"]
        if "actuator_setpoint" in self.current_values[_id]:
            current_setpoint = self.current_values[_id]["actuator_setpoint"]
            setpoint_preferred_value = current_setpoint["preferred_value"]

            csp = current_setpoint
            if "acceptable_values" in csp:
                current_acceptable_values = csp["acceptable_values"]
                discrete_flexibility = True
            if ("min_value" in csp and "max_value" in csp):
                current_min_value = csp["min_value"]
                current_max_value = csp["max_value"]
                continuous_flexibilty = True

        # Directly use preferred value of setpoint if no schedule is present.
        if current_schedule is None:
            actuator_value = setpoint_preferred_value

        # Directly use schedule value if no setpoint is given.
        if current_setpoint is None:
            actuator_value = schedule_value

        if current_schedule and current_setpoint:
            # for discrete datapoints.
            if discrete_flexibility:
                # No restrictions from acceptable values.
                if current_acceptable_values is None:
                    actuator_value = schedule_value
                # No sensor message received yet to verify we are in the
                # accepted range.
                elif current_sensor_value is None:
                    actuator_value = schedule_value
                # Last sensor value lays in allowed values, keep the schedule
                elif current_sensor_value in current_acceptable_values:
                    actuator_value = schedule_value
                # Anything else, especially the last sensor value is not
                # acceptable, fall back to preferred value.
                else:
                    actuator_value = setpoint_preferred_value

            # for continuous datapoints.
            elif continuous_flexibilty:
                # No sensor message received yet to verify we are in the
                # accepted range.
                #
                # Make the if cascades shorter and prevent line breaks.
                # Used only in this block
                c_s_v = current_sensor_value
                c_min_v = current_min_value
                c_max_v = current_max_value
                if c_s_v is None:
                    actuator_value = schedule_value
                # No restrictions, always check for None first to prevent
                # Type error when comparing int/floats with None
                elif c_min_v is None and c_max_v is None:
                    actuator_value = schedule_value
                elif c_min_v is None:
                    if c_s_v <= c_max_v:
                        actuator_value = schedule_value
                    else:
                        actuator_value = setpoint_preferred_value
                elif c_max_v is None:
                    if c_s_v >= c_min_v:
                        actuator_value = schedule_value
                    else:
                        actuator_value = setpoint_preferred_value
                elif c_s_v >= c_min_v and c_s_v <= c_max_v:
                    actuator_value = schedule_value
                # Anything else, especially the last sensor value out of the
                # accepted range, fall back to preferred value.
                else:
                    actuator_value = setpoint_preferred_value

            # Ignore setpoint if no flexibiltiy is defined.
            else:
                actuator_value = setpoint_preferred_value

        # Compare actuator value with last value sent, and send an update
        # if the value has changed.
        if ("actuator_value" not in self.current_values[_id] or
                actuator_value != self.current_values[_id]["actuator_value"]):
            actuator_value_msg = {
                "value": actuator_value,
                "timestamp": self.timestamp_now()
            }
            self.client.publish(
                actuator_value_topic,
                json.dumps(actuator_value_msg)
            )
            self.current_values[_id]["actuator_value"] = actuator_value

    def add_timer(self, topic, timer):
        """
        Add a timer the collecting object.

        Arguements:
        -----------
        topic: str
            The topic on which the schedule/sepoint has been received that
            led to the creation of these timers.
        timer: Threading.Timer object
            The timer object after it has been started.
        """
        if topic not in self.timers_per_topic:
            self.timers_per_topic[topic] = []
        self.timers_per_topic[topic].append(timer)

    def cancel_timers(self, topic):
        """
        Cancel all timers that are stored under the topic

        Arguements:
        -----------
        topic: str
            The topic on which the schedule/sepoint has been received that
            led to the creation of these timers.
        """
        if topic in self.timers_per_topic:
            timers = self.timers_per_topic.pop(topic)
            for timer in timers:
                timer.cancel()


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
