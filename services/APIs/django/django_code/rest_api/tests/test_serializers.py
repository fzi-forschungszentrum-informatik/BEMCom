"""
TODO Implement tests for these serializers:
    - DatapointSerializer
    - DatapointScheduleSerializer
    - DatapointSetpointSerializer
"""
import os
import json
import logging

import pytest

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    os.environ['DJANGO_SETTINGS_MODULE'] = 'general_configuration.settings'
    os.chdir('../..')
    setup()

from main.models.datapoint import Datapoint
from main.utils import datetime_from_timestamp
from main.connector_mqtt_integration import ConnectorMQTTIntegration
from main.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient
from main.tests.helpers import connector_factory, datapoint_factory
from rest_api.serializers import DatapointValueSerializer

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def value_serializer_setup(request, django_db_setup, django_db_blocker):
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
    cmi = ConnectorMQTTIntegration(
        mqtt_client=fake_client_1
    )

    test_connector = connector_factory("test_connector7")

    # Inject objects into test class.
    request.cls.test_connector = test_connector
    yield

    # Remove DB entries, as the restore command below does not seem to work.
    test_connector.delete()

    # Close connections and objects.
    cmi.disconnect()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures('value_serializer_setup')
class TestDatapointValueSerializer():

    def test_to_representation(self):
        """
        Check that the value part of a datapoint is converted as expected.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.last_value = "Test Value"
        timestamp = 1585092224000
        dp.last_value_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        expected_data = {
            "value": dp.last_value,
            "timestamp": timestamp,
        }

        serializer = DatapointValueSerializer(dp)
        assert serializer.data == expected_data

    def test_to_representation_for_none(self):
        """
        Check that the value part of a datapoint works if value and timestamp
        fields are None, which happens if we haven't received any update from
        the connector yet.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.save()

        expected_data = {
            "value": None,
            "timestamp": None,
        }

        serializer = DatapointValueSerializer(dp)
        assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that value must be given, and not giving timestamp is ok.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.save()

        test_data = json.loads('{}')
        serializer = DatapointValueSerializer(dp, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "value" in caught_execption.detail
        assert "timestamp" not in caught_execption.detail

    def test_numeric_value_validated(self):
        """
        Check that for numeric data_format values, only numeric values are
        accepted.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.allowed_values = '["not a number"]'
        dp.save()

        numeric_data_formats = [
            "generic_numeric",
            "continuous_numeric",
            "discrete_numeric",
        ]
        for data_format in numeric_data_formats:
            dp.data_format = data_format
            dp.save()

            test_data = json.loads('{"value": "not a number"}')
            serializer = DatapointValueSerializer(dp, data=test_data)
            caught_execption = None
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "value" in caught_execption.detail

        # Also verify the oposite, that text values are not rejected
        text_data_formats = [
            "generic_text",
            "discrete_text",
        ]
        for data_format in text_data_formats:
            dp.data_format = data_format
            dp.save()

            test_data = json.loads('{"value": "not a number"}')
            serializer = DatapointValueSerializer(dp, data=test_data)
            caught_execption = None
            try:
                assert serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is None

    def test_value_in_min_max(self):
        """
        Check that for continous numeric datapoints only those values are
        accepted that reside within the min/max bound, at least if min/max
        are set.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {"min": 1.00, "max": 3.00, "value": 2.00},
            {"min": None, "max": None, "value": 2.00},
            {"min": 1.00, "max": 3.00, "value": None},
            {"min": None, "max": 3.00, "value": 0.00},
            {"min": 1.00, "max": None, "value": 4.00},
        ]
        for valid_combination in valid_combinations:
            dp.min_value = valid_combination["min"]
            dp.max_value = valid_combination["max"]
            dp.save()

            test_data = {"value": valid_combination["value"]}
            serializer = DatapointValueSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_value_in_min_max failed for valid combination %s",
                    str(valid_combination)
                )
            assert is_valid

        invalid_combinations = [
            {"min": 1.00, "max": 3.00, "value": 4.00},
            {"min": 1.00, "max": 3.00, "value": 0.00},
            {"min": None, "max": 3.00, "value": 4.00},
            {"min": 1.00, "max": None, "value": 0.00},
        ]
        for invalid_combination in invalid_combinations:
            dp.min_value = invalid_combination["min"]
            dp.max_value = invalid_combination["max"]

            test_data = {"value": invalid_combination["value"]}
            serializer = DatapointValueSerializer(dp, data=test_data)

            caught_execption = None
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            if caught_execption is None:
                logger.error(
                    "test_value_in_min_max failed for invalid combination %s",
                    str(invalid_combination)
                )

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "value" in caught_execption.detail

    def test_value_in_allowed_values(self):
        """
        Check that for discrete valued datapoints only those values are
        accepted that have one of the accepted values.
        """
        dp = datapoint_factory(self.test_connector)
        dp.description = "A sensor datapoint for testing"
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {
                "value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": '[1.0, 2.0, 3.0]'
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[1, 2, 3]'
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": '["OK", "Done"]'
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": '[null, "Nope"]'
            },
        ]
        for valid_combination in valid_combinations:
            dp.data_format = valid_combination["data_format"]
            dp.allowed_values = valid_combination["allowed_values"]
            dp.save()

            test_data = {"value": valid_combination["value"]}
            serializer = DatapointValueSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_value_in_allowed_values failed for valid "
                    "combination %s",
                    str(valid_combination)
                )
            assert is_valid

        invalid_combinations = [
            {
                "value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": '[1.0, 3.0]'
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[1, 3]'
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[]'
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": '["NotOK", "OK "]'
            },
            {
                "value": "",
                "data_format": "discrete_text",
                "allowed_values": '["OK"]'
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": '["OK"]'
            },
            # These should be rejected but not trigger an exception due to
            # allowed values cannot be parsed by json.
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": None
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": ""
            },
        ]
        for invalid_combination in invalid_combinations:
            dp.data_format = invalid_combination["data_format"]
            dp.allowed_values = invalid_combination["allowed_values"]
            dp.save()

            test_data = {"value": invalid_combination["value"]}
            serializer = DatapointValueSerializer(dp, data=test_data)

            caught_execption = None
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            if caught_execption is None:
                logger.exception(
                    "test_value_in_allowed_values failed for invalid "
                    "combination %s",
                    str(valid_combination)
                )

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "value" in caught_execption.detail


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
