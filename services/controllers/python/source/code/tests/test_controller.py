import os
import json
import time

import pytest

import controller as controller_package
from tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient


@pytest.fixture(scope="class")
def controller_setup(request):
    """
    Set up the MQTT Broker and Controller for all the tests.
    """

    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)

    # Setup Broker and controller, store each received message in an extra
    # object to make it available to the tests.
    last_msgs = {"test": 1}
    userdata = {"last_msgs": last_msgs}

    def on_message(client, userdata, msg):
        last_msgs = userdata["last_msgs"]
        last_msgs[msg.topic] = json.loads(msg.payload)

    mqtt_client = fake_client_1(userdata=userdata)
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883)
    mqtt_client.loop_start()

    mqtt_config_topic = "python_controller/controlled_datapoints"
    # A fake timstamp assumed as now, to simplify tests.
    # This is roughly January, 26th 2020.
    timestamp_now = 1580000000000
    controller = controller_package.Controller(
        mqtt_broker_host="locahost",
        mqtt_broker_port=1883,
        mqtt_config_topic=mqtt_config_topic,
        mqtt_client=fake_client_2,
        timestamp_now=lambda: timestamp_now,
    )

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.controller = controller
    request.cls.mqtt_config_topic = mqtt_config_topic
    request.cls.timestamp_now = timestamp_now
    request.cls.last_msgs = last_msgs
    yield


@pytest.mark.usefixtures("controller_setup")
class TestController:
    def test_connected_to_message_broker(self):
        """
        Test that the controller connects to the message broker after startup.

        Here, as only two clients are created in setup, if both are connected
        there should be exactly two entries in connected_clients.
        """
        connected_clients = self.mqtt_client.fake_broker.connected_clients
        assert len(connected_clients) == 2

    def test_connected_to_config_topic(self):
        """
        Test that the controller is connected to the config topic.
        """
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics
        assert self.mqtt_config_topic in subscribed_topics
        assert len(subscribed_topics[self.mqtt_config_topic]) != 0

    def test_config_msg_processed(self):
        """
        Verify that the config message is processed correctly.

        Here we expect that the controller would connect to the value topic
        for the sensor and setpoint and schedule topic of the actuator after
        receiving the config message.
        """
        config_msg = [
            {
                "sensor": {
                    "value": "test_connector/messages/1/value",
                },
                "actuator": {
                    "value": "test_connector/messages/2/value",
                    "setpoint": "test_connector/messages/2/setpoint",
                    "schedule": "test_connector/messages/2/schedule",
                },
            },
        ]

        # Send the config msg.
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # Finally verify that the controller has subscribed to all topics
        # for which we expect it and not more.
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics
        expected_subscribed = []
        expected_subscribed.append(config_msg[0]["sensor"]["value"])
        expected_subscribed.append(config_msg[0]["actuator"]["setpoint"])
        expected_subscribed.append(config_msg[0]["actuator"]["schedule"])
        for expected_topic in expected_subscribed:
            assert expected_topic in subscribed_topics
            assert len(subscribed_topics[expected_topic]) != 0

    def test_config_msg_updates(self):
        """
        Verify that the config message cauese updates correctly.

        I.e. that the conroller is not subscribed to topics that are not
        part of the config anymore.
        """
        config_msg = [
            {
                "sensor": {
                    "value": "test_connector/messages/1/value",
                },
                "actuator": {
                    "value": "test_connector/messages/2/value",
                    "setpoint": "test_connector/messages/2/setpoint",
                    "schedule": "test_connector/messages/2/schedule",
                },
            },
        ]

        # Send the config msg.
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        config_msg_2 = [
            {
                "sensor": {
                    "value": "test_connector/messages/3/value",
                },
                "actuator": {
                    "value": "test_connector/messages/4/value",
                    "setpoint": "test_connector/messages/4/setpoint",
                    "schedule": "test_connector/messages/4/schedule",
                },
            },
        ]

        # Send the config msg.
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg_2),
        )

        # Finally verify that the controller has subscribed to all topics
        # for which we expect it and not more.
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics
        expected_subscribed = []
        expected_subscribed.append(config_msg_2[0]["sensor"]["value"])
        expected_subscribed.append(config_msg_2[0]["actuator"]["setpoint"])
        expected_subscribed.append(config_msg_2[0]["actuator"]["schedule"])
        for expected_topic in expected_subscribed:
            assert expected_topic in subscribed_topics
            assert len(subscribed_topics[expected_topic]) != 0
        unexpected_subscribed = []
        unexpected_subscribed.append(config_msg[0]["sensor"]["value"])
        unexpected_subscribed.append(config_msg[0]["actuator"]["setpoint"])
        unexpected_subscribed.append(config_msg[0]["actuator"]["schedule"])
        for unexpected_topic in unexpected_subscribed:
            assert unexpected_topic not in subscribed_topics

    def test_actuator_value_correct_only_setpoint(self):
        """
        Verify that the preferred values of setpoints are sent to the actuator
        if no schedule message is present.
        """
        sensor_value_topic = "test_connector/messages/5/value"
        actuator_value_topic = "test_connector/messages/6/value"
        actuator_setpoint_topic = "test_connector/messages/6/setpoint"
        actuator_schedule_topic = "test_connector/messages/6/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # Check that if from_timestamp is None the message is sent asap to the
        # actuator
        expected_value = 21
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": expected_value,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check that if from_timestamp is past the message is sent asap to the
        # actuator
        expected_value = 22
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": self.timestamp_now - 1,
                    "to_timestamp": None,
                    "preferred_value": expected_value,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check that if to_timestamp is past the message is not sent.
        expected_value = 22
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": self.timestamp_now - 3,
                    "to_timestamp": self.timestamp_now - 2,
                    "preferred_value": 23,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check multi setpoints with two in the future.
        ev_instant = 24
        ev_future = 25
        ev_far_future = 26
        expected_delay = 0.25
        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": self.timestamp_now + 200,
                    "preferred_value": 24,
                },
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": self.timestamp_now + 400,
                    "preferred_value": 25,
                },
                {
                    "from_timestamp": self.timestamp_now + 400,
                    "to_timestamp": None,
                    "preferred_value": 26,
                },
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_future
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_far_future

        # Check that an empty setpoint clears an older one, i.e. deactivates
        # all the timers.
        ev_instant = 27
        ev_future = 28
        ev_far_future = 29
        expected_delay = 0.25
        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": self.timestamp_now + 200,
                    "preferred_value": 27,
                },
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": self.timestamp_now + 400,
                    "preferred_value": 28,
                },
                {
                    "from_timestamp": self.timestamp_now + 400,
                    "to_timestamp": None,
                    "preferred_value": 29,
                },
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant

        test_msg = {
            "timestamp": self.timestamp_now,
            "setpoint": [],
        }
        self.mqtt_client.publish(actuator_setpoint_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant

    def test_actuator_value_correct_only_schedule(self):
        """
        Verify that the values of schedules are sent to the actuator
        if no setpoint message is present.
        """
        sensor_value_topic = "test_connector/messages/7/value"
        actuator_value_topic = "test_connector/messages/8/value"
        actuator_setpoint_topic = "test_connector/messages/8/setpoint"
        actuator_schedule_topic = "test_connector/messages/8/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # Check that if from_timestamp is None the message is sent asap to the
        # actuator
        expected_value = 21
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "value": expected_value,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check that if from_timestamp is past the message is sent asap to the
        # actuator
        expected_value = 22
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now - 1,
                    "to_timestamp": None,
                    "value": expected_value,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check that if to_timestamp is past the message is not sent.
        expected_value = 22
        expected_delay = 0.00
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now - 3,
                    "to_timestamp": self.timestamp_now - 2,
                    "value": 23,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Check multi schedules with two in the future.
        ev_instant = 24
        ev_future = 25
        ev_far_future = 26
        expected_delay = 0.25
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": self.timestamp_now + 200,
                    "value": 24,
                },
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": self.timestamp_now + 400,
                    "value": 25,
                },
                {
                    "from_timestamp": self.timestamp_now + 400,
                    "to_timestamp": None,
                    "value": 26,
                },
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_future
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_far_future

        # Check that an empty schedule clears an older one, i.e. deactivates
        # all the timers.
        ev_instant = 27
        ev_future = 28
        ev_far_future = 29
        expected_delay = 0.25
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": self.timestamp_now + 200,
                    "value": 27,
                },
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": self.timestamp_now + 400,
                    "value": 28,
                },
                {
                    "from_timestamp": self.timestamp_now + 400,
                    "to_timestamp": None,
                    "value": 29,
                },
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant

        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [],
        }
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant

    def test_actuator_value_correct_no_flexibilty(self):
        """
        Verify that the values of schedules are ignored if a setpoint is
        present that has no flexibility.
        """
        sensor_value_topic = "test_connector/messages/9/value"
        actuator_value_topic = "test_connector/messages/10/value"
        actuator_setpoint_topic = "test_connector/messages/10/setpoint"
        actuator_schedule_topic = "test_connector/messages/10/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        value_setpoint = 21.0
        value_schedule = 22.0
        expected_value = value_setpoint
        expected_delay = 0.25
        # Setpoint message is valid immediatly
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                }
            ],
        }
        # Schedule is valid bit in future, to ensure that the setpoint is
        # already set once the schedule arrives.
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

    def test_actuator_value_discrete_flexibilty(self):
        """
        Verify that the preferred_value of setpoint is overwritten by schedule
        value if the datapoint is discrete and has flexbility.
        """
        sensor_value_topic = "test_connector/messages/11/value"
        actuator_value_topic = "test_connector/messages/12/value"
        actuator_setpoint_topic = "test_connector/messages/12/setpoint"
        actuator_schedule_topic = "test_connector/messages/12/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # acceptable_values will only allow schedule value to be sent if the
        # corresponding sensor value lays within it. If no sensor message  is
        # available yet the schedule value should be sent.
        value_setpoint = 21.0
        value_schedule = 22.0
        expected_value = value_schedule
        expected_delay = 0.25
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "acceptable_values": [21.0, 22.0],
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # acceptable_values will only allow schedule value to be sent if the
        # corresponding sensor value lays within it. the sensor value here is
        # within acceptable_values, the schedule value should be sent.
        value_setpoint = 23.0
        value_schedule = 24.0
        expected_value = value_schedule
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 23.0}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "acceptable_values": [23.0, 24.0],
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # acceptable_values will only allow schedule value to be sent if the
        # corresponding sensor value lays within it. the sensor value here is
        # not in acceptable_values, the schedule value should not be sent.
        value_setpoint = 25.0
        value_schedule = 26.0
        expected_value = value_setpoint
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 23.0}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "acceptable_values": [25.0, 26.0],
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # acceptable_values will only allow schedule value to be sent if the
        # corresponding sensor value lays within it. However, acceptable_values
        # is here None, means every sensor value is ok. The schedule value
        # should be sent.
        value_setpoint = 27.0
        value_schedule = 28.0
        expected_value = value_schedule
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 23.0}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "acceptable_values": None,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

    def test_actuator_value_continuous_flexibilty(self):
        """
        Verify that the preferred_value of setpoint is overwritten by schedule
        value if the datapoint is continuous and has flexbility.
        """
        sensor_value_topic = "test_connector/messages/13/value"
        actuator_value_topic = "test_connector/messages/14/value"
        actuator_setpoint_topic = "test_connector/messages/14/setpoint"
        actuator_schedule_topic = "test_connector/messages/14/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # min_values and max_values  will only allow schedule value to be sent
        # if the corresponding sensor value lays within it. If no sensor
        # message  is available yet the schedule value should be sent.
        value_setpoint = 21.0
        value_schedule = 22.0
        expected_value = value_schedule
        expected_delay = 0.25
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "min_value": 19.0,
                    "max_value": 20.0,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # min_values and max_values will only allow schedule value to be sent
        # if the corresponding sensor value lays within it. The sensor value
        # here is within the acceptable range, the schedule value should be
        # sent.
        value_setpoint = 23.0
        value_schedule = 24.0
        expected_value = value_schedule
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 24.0}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "min_value": 24.0,
                    "max_value": 24.0,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # min_values and max_values will only allow schedule value to be sent
        # if the corresponding sensor value lays within it. The sensor value
        # here is not within the acceptable range, the schedule value should
        # thus be not be sent.
        value_setpoint = 25.0
        value_schedule = 26.0
        expected_value = value_setpoint
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 24.0}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "min_value": 25.0,
                    "max_value": 25.0,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Extend test for checking sensor values above range. Resend the
        # schedule to trigger a new timer.
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 26.0}
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # min_values and max_values will only allow schedule value to be sent
        # if the corresponding sensor value lays within it. Here min_value
        # is None, means that schedule value should not be sent as long as the
        # sensor value is above max_value.
        value_setpoint = 27.0
        value_schedule = 28.0
        expected_value = value_setpoint
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 10e8}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "min_value": None,
                    "max_value": 25.0,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Now with a sensor value within range.
        expected_value = value_schedule
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": -10e8}
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # min_values and max_values will only allow schedule value to be sent
        # if the corresponding sensor value lays within it. Here max_value
        # is None, means that schedule value should not be sent as long as the
        # sensor value is below min_value.
        value_setpoint = 29.0
        value_schedule = 30.0
        expected_value = value_setpoint
        expected_delay = 0.25
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": -10e8}
        test_msg_setpoint = {
            "timestamp": self.timestamp_now,
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": None,
                    "preferred_value": value_setpoint,
                    "min_value": 25.0,
                    "max_value": None,
                }
            ],
        }
        test_msg_schedule = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": None,
                    "value": value_schedule,
                }
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(
            actuator_setpoint_topic, json.dumps(test_msg_setpoint)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

        # Now with a sensor value within range.
        expected_value = value_schedule
        test_msg_sensor = {"timestamp": self.timestamp_now, "value": 10e8}
        self.mqtt_client.publish(
            actuator_schedule_topic, json.dumps(test_msg_schedule)
        )
        self.mqtt_client.publish(
            sensor_value_topic, json.dumps(test_msg_sensor)
        )
        time.sleep(expected_delay)
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == expected_value

    def test_no_redudant_actuator_messages(self):
        """
        Verify that only actuator messages are sent if the value changes.
        """
        sensor_value_topic = "test_connector/messages/15/value"
        actuator_value_topic = "test_connector/messages/16/value"
        actuator_setpoint_topic = "test_connector/messages/16/setpoint"
        actuator_schedule_topic = "test_connector/messages/16/schedule"

        # Configure the controller to listen to the topics above.
        config_msg = [
            {
                "sensor": {
                    "value": sensor_value_topic,
                },
                "actuator": {
                    "value": actuator_value_topic,
                    "setpoint": actuator_setpoint_topic,
                    "schedule": actuator_schedule_topic,
                },
            },
        ]
        self.mqtt_client.publish(
            self.mqtt_config_topic,
            json.dumps(config_msg),
        )

        # A schedule with two identical values. The second value should not
        # trigger a second message as it carries no new information.
        ev_instant = 24
        expected_delay = 0.25
        test_msg = {
            "timestamp": self.timestamp_now,
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": self.timestamp_now + 200,
                    "value": 24,
                },
                {
                    "from_timestamp": self.timestamp_now + 200,
                    "to_timestamp": self.timestamp_now + 400,
                    "value": 24,
                },
            ],
        }
        self.mqtt_client.subscribe(actuator_value_topic)
        self.mqtt_client.publish(actuator_schedule_topic, json.dumps(test_msg))
        assert actuator_value_topic in self.last_msgs
        assert self.last_msgs[actuator_value_topic]["value"] == ev_instant

        # Remove the key to check that no new message is arrived.
        del self.last_msgs[actuator_value_topic]
        time.sleep(expected_delay)
        assert actuator_value_topic not in self.last_msgs


def test_sort_schedule_setpoint_items():
    l = [
        {"from_timestamp": 12344, "to_timestamp": None},
        {"from_timestamp": None, "to_timestamp": None},
        {"from_timestamp": None, "to_timestamp": 12334},
        {"from_timestamp": 123445, "to_timestamp": None},
    ]
    l_expected_sorted = [
        {"from_timestamp": None, "to_timestamp": 12334},
        {"from_timestamp": None, "to_timestamp": None},
        {"from_timestamp": 12344, "to_timestamp": None},
        {"from_timestamp": 123445, "to_timestamp": None},
    ]
    l_sorted = controller_package.sort_schedule_setpoint_items(l)
    assert l_sorted == l_expected_sorted
