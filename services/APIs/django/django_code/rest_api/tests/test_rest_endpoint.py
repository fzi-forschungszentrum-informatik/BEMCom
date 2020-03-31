"""
Here tests for the functionality provided by the REST endpoint, that is
functionality provided by the REST Api that a client must request.

TODO Extend tests with the following:
    - Add tests for the checker, i.e that put messages with missing fields are
      rejected.
    - Add tests for permission tests.
"""
import os
import json
import time

import pytest

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    os.environ['DJANGO_SETTINGS_MODULE'] = 'general_configuration.settings'
    os.chdir('../..')
    setup()

from rest_framework.test import APIClient

from main.utils import datetime_from_timestamp
from main.connector_mqtt_integration import ConnectorMQTTIntegration
from main.tests.helpers import connector_factory, datapoint_factory
from main.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient


@pytest.fixture(scope='class')
def rest_endpoint_setup(request, django_db_setup, django_db_blocker):
    """
    SetUp FakeMQTTBroker, ConnectorMQTTIntegration and APIClient for all
    tests targeting the API endpoints.

    This is significantly faster then using unittest's setUp and tearDown
    as those are executed for every test function, here only for the class
    as a whole.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    # This is not needed for the tests itself, but just to ensure that
    # adding datapoints and connectors succeeds.
    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)
    cmi = ConnectorMQTTIntegration(
        mqtt_client=fake_client_1
    )

    # Setup MQTT client endpoints for test.
    mqtt_client = fake_client_2(userdata={})
    mqtt_client.connect('localhost', 1883)
    mqtt_client.loop_start()

    test_connector = connector_factory("test_connector6")
    client = APIClient()

    # Inject objects into test class.
    request.cls.test_connector = test_connector
    request.cls.mqtt_client = mqtt_client
    request.cls.client = client
    yield

    # Close connections and objects.
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    cmi.disconnect()

    # Remove DB entries, as the restore command below does not seem to work.
    test_connector.delete()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures('rest_endpoint_setup')
class TestRESTEndpoint():
    """
    Here all tests targeting for functionality triggered by the client.

    TODO Extend the following tests:
        - Check that only active datapoints are returned
        - Check that only datapoints with permissions are returned.
        - Check that the datapoints list is as expected.
    """

    def test_get_datapoint_detail_for_sensor(self):
        """
        Request the data of one sensor datapoint from the REST API and
        check that the all expected fields are delivered.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.save()
        request = self.client.get("/datapoint/%s/" % dp.id)

        expected_data = {
            "id": dp.id,
            "type": "sensor",
            "data_format": "generic_text",
            "description": "A sensor datapoint for testing",
            "url": "http://testserver/datapoint/%s/" % dp.id,
            "value_url": "http://testserver/datapoint/%s/value/" % dp.id,
        }

        assert request.data == expected_data

    def test_get_datapoint_detail_for_actuator(self):
        """
        Request the data of one actuator datapoint from the REST API and
        check that the expected fields are delivered.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        request = self.client.get("/datapoint/%s/" % dp.id)

        expected_data = {
            "id": dp.id,
            "type": "actuator",
            "data_format": "generic_text",
            "description": "",
            "url": "http://testserver/datapoint/%s/" % dp.id,
            "value_url": "http://testserver/datapoint/%s/value/" % dp.id,
            "schedule_url": "http://testserver/datapoint/%s/schedule/" % dp.id,
            "setpoint_url": "http://testserver/datapoint/%s/setpoint/" % dp.id,
        }

        assert request.data == expected_data

    def test_get_datapoint_value_detail_for_sensor(self):
        """
        Request the latest datapoint value msg and check that all expected
        fields are delivered.
        """
        dp = datapoint_factory(self.test_connector)
        dp.last_value = "last_value!"
        timestamp = 1585092224000
        dp.last_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        request = self.client.get("/datapoint/%s/value/" % dp.id)

        expected_data = {
            "value": "last_value!",
            "timestamp": timestamp,
        }

        assert request.data == expected_data

    def test_get_datapoint_value_detail_for_sensor_with_empty(self):
        """
        Ensure that the value detail page handles missing values correclty
        by displaying them as None.
        """
        dp = datapoint_factory(self.test_connector)
        request = self.client.get("/datapoint/%s/value/" % dp.id)

        expected_data = {
            "value": None,
            "timestamp": None,
        }

        assert request.data == expected_data

    def test_put_datapoint_value_detail_rejected_for_sensor(self):
        """
        Check that it is not possible to write sensor message from the client.

        This does not make sense, sensor messages should only be generated
        by the devices.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.last_value = "last_value!"
        timestamp = 1585092224000
        dp.last_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        # Now put an update for the datapoint and check that the put was
        # denied as expected.
        update_msg = {
            "value": "updated_value!",
            "timestamp": 1585096161000,
        }
        request = self.client.put(
            "/datapoint/%s/value/" % dp.id,
            update_msg,
            format='json'
        )
        assert request.status_code == 405

    def test_put_datapoint_value_detail_for_actuator(self):
        """
        Write (PUT) a value message, that should trigger that the corresponding
        message is sent to the message broker and after that also stored in the
        database, from which it should be readable as usual.

        This should by definition only be possible for actuators.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.last_value = "last_value!"
        timestamp = 1585092224000
        dp.last_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        # Subscribe to the MQTT topic of the datapoint so we can check if the
        # expected message was sent.
        def on_message(client, userdata, msg):
            """
            Store the received message so we can test it's correctness later.
            """
            client.userdata[msg.topic] = json.loads(msg.payload)
        dp_mqtt_value_topic = dp.get_mqtt_topic()
        self.mqtt_client.subscribe(dp_mqtt_value_topic)
        self.mqtt_client.on_message = on_message

        # Now put an update for the datapoint and check that the put was
        # successful.
        update_msg = {
            "value": "updated_value!",
            "timestamp": 1585096161000,
        }
        request = self.client.put(
            "/datapoint/%s/value/" % dp.id,
            update_msg,
            format='json'
        )
        assert request.status_code == 200

        # Check if the message has been sent. This might happen in async, so
        # we may have to wait a little. If this code fails, the fault likely
        # resides in the mqtt_integration.
        waited_seconds = 0
        while dp_mqtt_value_topic not in self.mqtt_client.userdata:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected datapoint value message has not been published "
                    "on broker."
                )

        # Now that we know the message has been published on the broker,
        # verify it holds the expected information.
        assert self.mqtt_client.userdata[dp_mqtt_value_topic] == update_msg

        # After the MQTT message has now arrived the updated value should now
        # be available on the REST interface. As above this might happen async,
        # hence we might give the message a bit time to arrive.
        waited_seconds = 0
        while True:
            dp.refresh_from_db()
            if dp.last_value == update_msg["value"]:
                break

            time.sleep(0.005)
            waited_seconds += 0.005
            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected datapoint value message has not reached the DB."
                )

        request = self.client.get("/datapoint/%s/value/" % dp.id)
        assert request.data == update_msg

    def test_get_datapoint_schedule_detail_rejected_for_sensor(self):
        """
        Check that a schedule detail cannot be retrieved for a sensor, as
        this kind of message does only exist for actuators.
        """
        dp = datapoint_factory(self.test_connector)
        request = self.client.get("/datapoint/%s/setpoint/" % dp.id)

        assert request.status_code == 404

    def test_put_datapoint_schedule_detail_rejected_for_sensor(self):
        """
        Check that a schedule detail cannot be written for a sensor, as
        this kind of message does only exist for actuators.
        """
        dp = datapoint_factory(self.test_connector)

        # TODO: Correct this message.
        update_msg = {
            "value": "updated_value!",
            "timestamp": 1585096161000,
        }
        request = self.client.put(
            "/datapoint/%s/value/" % dp.id,
            update_msg,
            format='json'
        )

        assert request.status_code == 404

    def test_get_datapoint_schedule_detail_rejected_for_actuator(self):
        """
        TODO
        """
        assert False

    def test_put_datapoint_schedule_detail_rejected_for_actuator(self):
        """
        TODO
        """
        assert False

    def test_get_datapoint_setpoint_detail_rejected_for_sensor(self):
        """
        TODO
        """
        assert False

    def test_put_datapoint_setpoint_detail_rejected_for_sensor(self):
        """
        TODO
        """
        assert False

    def test_get_datapoint_setpoint_detail_rejected_for_actuator(self):
        """
        TODO
        """
        assert False

    def test_put_datapoint_setpoint_detail_rejected_for_actuator(self):
        """
        TODO
        """
        assert False


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
