import os
from datetime import datetime

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
def datapoint_detail_setup(request, django_db_setup, django_db_blocker):
    """
    SetUp Fake MQTT Broker and ConnectorMQTTIntegration for all tests in
    TestConnectorIntegration.

    This is significantly faster then using unittest's setUp and tearDown
    as those are executed for every test function, here only for the class
    as a whole.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    # This is not needed for the tests itself, but just to prevent that
    # adding datapoints and connectors succeeds.
    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    _ = ConnectorMQTTIntegration(
        mqtt_client=fake_client_1
    )

    test_connector = connector_factory("test_connector6")
    client = APIClient()

    # Inject objects into test class.
    request.cls.test_connector = test_connector
    request.cls.client = client
    yield

    # Remove DB entries, as the restore command below does not seem to work.
    test_connector.delete()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()

@pytest.mark.usefixtures('datapoint_detail_setup')
class TestDatapointDetails():
    """
    Here the test cases for datapoint detail pages.

    TODO:
        - Check that only active datapoints are returned
        - Check that only datapoints with permissions are returned.
        - Check that the datapoints list is as expected.
    """

    def test_datapoint_detail_for_sensor(self):
        """
        Request the data of one sensor datapoint from the REST API and
        ensure that the expected fields have been delivered.
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

    def test_datapoint_value_detail(self):
        """
        Ensure that the value detail page contains the correct data.
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

    def test_datapoint_value_detail_with_empty(self):
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

    def test_datapoint_detail_for_actuator(self):
        """
        Request the data of one actuator datapoint from the REST API and
        ensure that the expected fields have been delivered.
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

    def test_setpoint_detail_for_actuator(self):
        """
        Test that the setpoint detail is contains the expected data for
        actuator datapoints.
        TODO
        """
        assert "TODO" == "Done"

    def test_schedule_detail_for_actuator(self):
        """
        Test that the schedule detail is contains the expected data for
        actuator datapoints.
        TODO
        """
        assert "TODO" == "Done"

    def test_no_setpoint_detail_for_sensor(self):
        """
        Test that no setpoint is returned for sensors.
        """
        dp = datapoint_factory(self.test_connector)
        request = self.client.get("/datapoint/%s/setpoint/" % dp.id)

        assert request.status_code == 404

    def test_no_schedule_detail_for_sensor(self):
        """
        Test that no schedule is returned for sensors.
        """
        dp = datapoint_factory(self.test_connector)
        request = self.client.get("/datapoint/%s/schedule/" % dp.id)

        assert request.status_code == 404


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
