import os

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
