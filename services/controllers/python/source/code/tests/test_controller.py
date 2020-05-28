import os
import json

import pytest

import controller as controller_package
from tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient


@pytest.fixture(scope='class')
def controller_setup(request):
    """
    Set up the MQTT Broker and Controller for all the tests.
    """

    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)

    # Setup Broker and controller.
    mqtt_client = fake_client_1()
    mqtt_client.connect('localhost', 1883)
    mqtt_client.loop_start()

    mqtt_config_topic = "python_controller/controlled_datapoints"
    controller = controller_package.Controller(
        mqtt_broker_host="locahost",
        mqtt_broker_port=1883,
        mqtt_config_topic=mqtt_config_topic,
        mqtt_client=fake_client_2
    )

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.controller = controller
    request.cls.mqtt_config_topic = mqtt_config_topic
    yield


@pytest.mark.usefixtures('controller_setup')
class TestController():

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
                }
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
                }
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
                }
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