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
from rest_api.serializers import DatapointScheduleSerializer
from rest_api.serializers import DatapointSetpointSerializer

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
                is_valid = False
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
                is_valid = False
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


@pytest.fixture(scope='class')
def schedule_serializer_setup(request, django_db_setup, django_db_blocker):
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

    test_connector = connector_factory("test_connector8")

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


@pytest.mark.usefixtures('schedule_serializer_setup')
class TestDatapointScheduleSerializer():

    def test_to_representation(self):
        """
        Check that the schedule part of a datapoint is converted as expected.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        last_schedule = [
            {
                "from_timestamp": None,
                "to_timestamp": 1564489613491,
                'value': 21
            },
            {
                "from_timestamp": 1564489613491,
                "to_timestamp": None,
                'value': None
            }
        ]
        dp.last_schedule = json.dumps(last_schedule)
        timestamp = 1564489613491
        dp.last_schedule_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        expected_data = {
            "schedule": last_schedule,
            "timestamp": timestamp,
        }

        serializer = DatapointScheduleSerializer(dp)
        assert serializer.data == expected_data

    def test_to_representation_for_none(self):
        """
        Check that the schedule part of a datapoint works if value and
        timestamp fields are None, which happens if we haven't received any
        schedule yet.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        expected_data = {
            "schedule": None,
            "timestamp": None,
        }

        serializer = DatapointScheduleSerializer(dp)
        assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that schedule must be given, and not giving timestamp is ok.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        test_data = {}
        serializer = DatapointScheduleSerializer(dp, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        assert "timestamp" not in caught_execption.detail

    def test_schedule_validated_as_correct_json_or_null(self):
        """
        Check that the schedule is validated to be a parsable as json.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # First this is correct json.
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613491,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        assert serializer.is_valid()

        # This is also ok.
        test_data = {
            "schedule": None
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        assert serializer.is_valid()

    def test_schedule_validated_as_list(self):
        """
        Check that the schedule is validated to be a list.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # This is correct json but not a list of schedule items.
        test_data = {
            "schedule": {"Nope": 1}
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "not a list of schedule items." in exception_detail

    def test_schedule_items_validated_as_dict(self):
        """
        Check that the schedule items are validated to be dicts.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # This is correct json but not a list of schedule items.
        test_data = {
            "schedule": ["Nope", 1]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "is not a Dict." in exception_detail

    def test_schedule_items_validated_for_expected_keys(self):
        """
        Check that the schedule items are validated to contain only the
        expected keys and nothing else.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # Missing from_timestamp
        test_data = {
            "schedule": [
                {
                    "to_timestamp": 1564489613491,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "from_timestamp" in exception_detail

        # Missing to_timestamp
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "to_timestamp" in exception_detail

        # Missing value
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613491
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "value" in exception_detail

        # Additional value
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613491,
                    "value": "not a number",
                    "not_expected_field": "Should fail"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "Found unexpected key" in exception_detail

    def test_numeric_value_of_schedule_validated(self):
        """
        Check that for numeric data_format values, only numeric values are
        accepted within schedules.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
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

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": "not a number"
                    }
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)
            caught_execption = None
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "schedule" in caught_execption.detail
            exception_detail = str(caught_execption.detail["schedule"])
            assert "cannot be parsed to float" in exception_detail

        # Also verify the oposite, that text values are not rejected
        text_data_formats = [
            "generic_text",
            "discrete_text",
        ]
        for data_format in text_data_formats:
            dp.data_format = data_format
            dp.save()

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": "not a number"
                    }
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)
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
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
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

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": valid_combination["value"]
                    }
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_value_in_min_max failed for valid combination %s",
                    str(valid_combination)
                )
                is_valid = False
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

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": invalid_combination["value"]
                    },
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)

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
            assert "schedule" in caught_execption.detail
            exception_detail = str(caught_execption.detail["schedule"])
            assert "numeric datapoint" in exception_detail

    def test_value_in_allowed_values(self):
        """
        Check that for discrete valued datapoints only those values are
        accepted that have one of the accepted values.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
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

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": valid_combination["value"]
                    },
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_value_in_allowed_values failed for valid "
                    "combination %s",
                    str(valid_combination)
                )
                is_valid = False
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
        ]
        for invalid_combination in invalid_combinations:
            dp.data_format = invalid_combination["data_format"]
            dp.allowed_values = invalid_combination["allowed_values"]
            dp.save()

            test_data = {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "value": valid_combination["value"]
                    },
                ]
            }
            serializer = DatapointScheduleSerializer(dp, data=test_data)

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
            assert "schedule" in caught_execption.detail
            exception_detail = str(caught_execption.detail["schedule"])
            assert "discrete datapoint" in exception_detail

    def test_timestamps_are_validated_against_each_other(self):
        """
        Check that if from_timestamp and to_timestamp is set not None,
        it is validated that to_timestamp is larger.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # Missing from_timestamp
        test_data = {
            "schedule": [
                {
                    "from_timestamp": 1564489613492,
                    "to_timestamp": 1564489613491,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "timestamp must be larger" in exception_detail

    def test_timestamps_are_validated_to_be_numbers(self):
        """
        Check that if from_timestamp and to_timestamp are validated to be
        None or convertable to a number.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": "not 1564489613491",
                    "value": 'not a number'
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "could not be parsed to integer" in exception_detail

        test_data = {
            "schedule": [
                {
                    "from_timestamp": "not 1564489613491",
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "could not be parsed to integer" in exception_detail

    def test_timestamps_not_in_milliseconds_yield_error(self):
        """
        Check that an error message is yielded if the timestamp is in
        obviously not in milliseconds.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.save()

        # timestamp in seconds.
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "seems unreasonably low" in exception_detail

        test_data = {
            "schedule": [
                {
                    "from_timestamp": 1564489613,
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "seems unreasonably low" in exception_detail

        # timestamp in microseconds.
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613000000,
                    "value": "not a number'"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "seems unreasonably high" in exception_detail

        test_data = {
            "schedule": [
                {
                    "from_timestamp": 1564489613000000,
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ]
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        exception_detail = str(caught_execption.detail["schedule"])
        assert "seems unreasonably high" in exception_detail


@pytest.fixture(scope='class')
def setpoint_serializer_setup(request, django_db_setup, django_db_blocker):
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

    test_connector = connector_factory("test_connector8")

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


@pytest.mark.usefixtures('setpoint_serializer_setup')
class TestDatapointSetpointSerializer():

    def test_to_representation(self):
        """
        Check that the setpoint part of a datapoint is converted as expected.

        Test discrete_numveric and continuous_numeric cases to cover all
        possible fields.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for schedule testing."
        dp.data_format = "discrete_numeric"
        last_setpoint = [
            {
                "from_timestamp": None,
                "to_timestamp": 1564489613491,
                'preferred_value': 21,
                'acceptable_values': [20.5, 21, 21.5],

            },
            {
                "from_timestamp": 1564489613491,
                "to_timestamp": None,
                'preferred_value': None,
                'acceptable_values': [None]
            }
        ]
        dp.last_setpoint = json.dumps(last_setpoint)
        timestamp = 1564489613491
        dp.last_setpoint_timestamp = datetime_from_timestamp(timestamp)
        dp.save()

        expected_data = {
            "setpoint": last_setpoint,
            "timestamp": timestamp,
        }

        serializer = DatapointSetpointSerializer(dp)
        assert serializer.data == expected_data

        dp.data_format = "continuous_numeric"
        last_setpoint = [
            {
                "from_timestamp": None,
                "to_timestamp": 1564489613491,
                'preferred_value': 21,
                'min_value': 20,
                'max_value': 22,

            },
            {
                "from_timestamp": 1564489613491,
                "to_timestamp": None,
                'preferred_value': None,
                'min_value': None,
                'max_value': None,
            }
        ]
        dp.last_setpoint = json.dumps(last_setpoint)
        dp.save()

        expected_data = {
            "setpoint": last_setpoint,
            "timestamp": timestamp,
        }

        serializer = DatapointSetpointSerializer(dp)
        assert serializer.data == expected_data

    def test_to_representation_for_none(self):
        """
        Check that the setpoint part of a datapoint works if value and
        timestamp fields are None, which happens if we haven't received any
        setpoint yet.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        expected_data = {
            "setpoint": None,
            "timestamp": None,
        }

        serializer = DatapointSetpointSerializer(dp)
        assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that setpoint must be given, and not giving timestamp is ok.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        test_data = {}
        serializer = DatapointSetpointSerializer(dp, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        assert "timestamp" not in caught_execption.detail

    def test_setpoint_validated_as_correct_json_or_null(self):
        """
        Check that the setpoint is validated to be a parsable as json.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        # First this is correct json.
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613491,
                    'preferred_value': 'not a number'
                },
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        assert serializer.is_valid()

        # This is also ok.
        test_data = {
            "setpoint": None
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        assert serializer.is_valid()

    def test_setpoint_validated_as_list(self):
        """
        Check that the setpoint is validated to be a list.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        # This is correct json but not a list of setpoint items.
        test_data = {
            "setpoint": {"Nope": 1}
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "not a list of setpoint items." in exception_detail

    def test_setpoint_items_validated_as_dict(self):
        """
        Check that the setpoint items are validated to be dicts.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        # This is correct json but not a list of setpoint items.
        test_data = {
            "setpoint": ["Nope", 1]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "is not a Dict." in exception_detail

    def test_setpoint_items_validated_for_expected_keys(self):
        """
        Check that the setpoint items are validated to contain only the
        expected keys and nothing else.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        always_required_keys = [
            "from_timestamp",
            "to_timestamp",
            "preferred_value"
        ]
        only_con_keys = [
            "min_value",
            "max_value"
        ]
        only_dis_keys = [
            "acceptable_values"
        ]
        # Here a listing which keys must be given in a setpoint message per
        # data_format.
        required_keys_per_data_format = {
            "generic_numeric": always_required_keys,
            "continuous_numeric": always_required_keys + only_con_keys,
            "discrete_numeric": always_required_keys + only_dis_keys,
            "generic_text": always_required_keys,
            "discrete_text": always_required_keys + only_dis_keys,
        }

        # Here a list of keys which will be tested as extra keys, that should
        # be refused. The keys that are valid for other data_formats are of
        # course especially interesting.
        nvk = ["no_valid_key"]
        unexpected_keys_per_data_format = {
            "generic_numeric": nvk + only_con_keys + only_dis_keys,
            "continuous_numeric": nvk + only_dis_keys,
            "discrete_numeric": nvk + only_con_keys,
            "generic_text": nvk + only_con_keys + only_dis_keys,
            "discrete_text": nvk + only_con_keys,
        }

        # Here the dummy values for all fields used above.
        setpoint_all_fields = {
            "from_timestamp": None,
            "to_timestamp": 1564489613491,
            "preferred_value": 21,
            "acceptable_values": [20.5, 21, 21.5],
            "min_value": 20.5,
            "max_value": 21.5,
            "no_valid_key": 1337
        }

        for data_format in required_keys_per_data_format:
            dp.data_format = data_format
            dp.save()
            required_keys = required_keys_per_data_format[data_format]

            # Now construct per data_format test cases to verify that every
            # missing field is found for every data_format.
            for key_left_out in required_keys:
                setpoint = {}
                for key in required_keys:
                    if key == key_left_out:
                        continue
                    setpoint[key] = setpoint_all_fields[key]

                test_data = {
                    "setpoint": [setpoint]
                }

                serializer = DatapointSetpointSerializer(dp, data=test_data)
                caught_execption = None
                try:
                    serializer.is_valid(raise_exception=True)
                    logger.error(
                        "Failed to identify required key (%s) while validating"
                        "setpoint data for data_format (%s)" %
                        (key_left_out, data_format)
                    )
                except Exception as e:
                    caught_execption = e

                assert caught_execption is not None
                assert caught_execption.status_code == 400
                assert "setpoint" in caught_execption.detail
                exception_detail = str(caught_execption.detail["setpoint"])
                assert key_left_out in exception_detail

        # Now construct test cases to verify that additional unexpected
        # keys are rejected.
        for data_format in unexpected_keys_per_data_format:
            dp.data_format = data_format
            dp.save()
            unexpected_keys = unexpected_keys_per_data_format[data_format]
            required_keys = required_keys_per_data_format[data_format]

            setpoint = {}
            for unexpected_key in unexpected_keys:
                for key in required_keys:
                    setpoint[key] = setpoint_all_fields[key]

                setpoint[unexpected_key] = setpoint_all_fields[unexpected_key]

                test_data = {
                    "setpoint": [setpoint]
                }

                serializer = DatapointSetpointSerializer(dp, data=test_data)
                caught_execption = None
                try:
                    serializer.is_valid(raise_exception=True)
                    logger.error(
                        "Failed to identify unexpected key (%s) while "
                        " validating setpoint data for data_format (%s)" %
                        (unexpected_key, data_format)
                    )
                except Exception as e:
                    caught_execption = e

                assert caught_execption is not None
                assert caught_execption.status_code == 400
                assert "setpoint" in caught_execption.detail
                exception_detail = str(caught_execption.detail["setpoint"])
                assert "Found unexpected key" in exception_detail

    def test_numeric_value_of_setpoint_validated(self):
        """
        Check that for numeric data_formats, only numeric preferred_values are
        accepted within setpoints.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.allowed_values = '["not a number"]'
        dp.save()

        # Here a listing which keys must be given in a setpoint message per
        # data_format.
        always_required_keys = [
            "from_timestamp",
            "to_timestamp",
            "preferred_value"
        ]
        only_con_keys = [
            "min_value",
            "max_value"
        ]
        only_dis_keys = [
            "acceptable_values"
        ]
        required_keys_per_data_format = {
            "generic_numeric": always_required_keys,
            "continuous_numeric": always_required_keys + only_con_keys,
            "discrete_numeric": always_required_keys + only_dis_keys,
            "generic_text": always_required_keys,
            "discrete_text": always_required_keys + only_dis_keys,
        }

        # Here the dummy values for all fields used above.
        setpoint_all_fields = {
            "from_timestamp": None,
            "to_timestamp": 1564489613491,
            "preferred_value": "not a number",
            "acceptable_values": ["not a number"],
            "min_value": 20.5,
            "max_value": 21.5,
        }

        numeric_data_formats = [
            "generic_numeric",
            "continuous_numeric",
            "discrete_numeric",
        ]
        for data_format in numeric_data_formats:
            dp.data_format = data_format
            dp.save()
            required_keys = required_keys_per_data_format[data_format]
            setpoint = {}
            for key in required_keys:
                setpoint[key] = setpoint_all_fields[key]

            test_data = {
                "setpoint": [setpoint]
            }

            serializer = DatapointSetpointSerializer(dp, data=test_data)
            caught_execption = None
            try:
                serializer.is_valid(raise_exception=True)
                logger.error(
                    "Failed to identify non numeric value while "
                    "validating setpoint data for data_format (%s)" %
                    data_format
                )
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "setpoint" in caught_execption.detail
            exception_detail = str(caught_execption.detail["setpoint"])
            assert "cannot be parsed to float" in exception_detail

        # Also verify the oposite, that text values are not rejected
        text_data_formats = [
            "generic_text",
            "discrete_text",
        ]
        for data_format in text_data_formats:
            dp.data_format = data_format
            dp.save()
            required_keys = required_keys_per_data_format[data_format]
            setpoint = {}
            for key in required_keys:
                setpoint[key] = setpoint_all_fields[key]

            test_data = {
                "setpoint": [setpoint]
            }

            serializer = DatapointSetpointSerializer(dp, data=test_data)
            caught_execption = None
            try:
                assert serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e
                logger.exception("")

            assert caught_execption is None

    def test_preferred_value_in_min_max(self):
        """
        Check that for continous numeric datapoints only those preferred_value
        are accepted that reside within the min/max bound, at least if min/max
        are set.

        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {"min": 1.00, "max": 3.00, "preferred_value": 2.00},
            {"min": None, "max": None, "preferred_value": 2.00},
            {"min": 1.00, "max": 3.00, "preferred_value": None},
            {"min": None, "max": 3.00, "preferred_value": 0.00},
            {"min": 1.00, "max": None, "preferred_value": 4.00},
        ]
        for valid_combination in valid_combinations:
            dp.min_value = valid_combination["min"]
            dp.max_value = valid_combination["max"]
            dp.save()

            test_data = {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "preferred_value":
                            valid_combination["preferred_value"],
                        "min_value": None,
                        "max_value": None
                    }
                ]
            }
            serializer = DatapointSetpointSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_value_in_min_max failed for valid combination %s",
                    str(valid_combination)
                )
                is_valid = False
            assert is_valid

        invalid_combinations = [
            {"min": 1.00, "max": 3.00, "preferred_value": 4.00},
            {"min": 1.00, "max": 3.00, "preferred_value": 0.00},
            {"min": None, "max": 3.00, "preferred_value": 4.00},
            {"min": 1.00, "max": None, "preferred_value": 0.00},
        ]
        for invalid_combination in invalid_combinations:
            dp.min_value = invalid_combination["min"]
            dp.max_value = invalid_combination["max"]

            test_data = {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "preferred_value":
                            invalid_combination["preferred_value"],
                        "min_value": None,
                        "max_value": None
                    },
                ]
            }
            serializer = DatapointSetpointSerializer(dp, data=test_data)

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
            assert "setpoint" in caught_execption.detail
            exception_detail = str(caught_execption.detail["setpoint"])
            assert "numeric datapoint" in exception_detail

    def test_preferred_value_in_allowed_values(self):
        """
        Check that for discrete valued datapoints only those preferred_value
        are accepted that have one of the accepted values.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {
                "preferred_value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": '[1.0, 2.0, 3.0]'
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[1, 2, 3]'
            },
            {
                "preferred_value": "OK",
                "data_format": "discrete_text",
                "allowed_values": '["OK", "Done"]'
            },
            {
                "preferred_value": None,
                "data_format": "discrete_text",
                "allowed_values": '[null, "Nope"]'
            },
        ]
        for valid_combination in valid_combinations:
            dp.data_format = valid_combination["data_format"]
            dp.allowed_values = valid_combination["allowed_values"]
            dp.save()

            test_data = {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "preferred_value":
                            valid_combination["preferred_value"],
                        "acceptable_values":
                            [valid_combination["preferred_value"]]
                    }
                ]
            }
            serializer = DatapointSetpointSerializer(dp, data=test_data)

            try:
                is_valid = serializer.is_valid(raise_exception=True)
            except Exception:
                logger.exception(
                    "test_preferred_value_in_allowed_values failed for valid "
                    "combination %s",
                    str(valid_combination)
                )
                is_valid = False
            assert is_valid

        invalid_combinations = [
            {
                "preferred_value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": '[1.0, 3.0]'
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[1, 3]'
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": '[]'
            },
            {
                "preferred_value": "OK",
                "data_format": "discrete_text",
                "allowed_values": '["NotOK", "OK "]'
            },
            {
                "preferred_value": "",
                "data_format": "discrete_text",
                "allowed_values": '["OK"]'
            },
            {
                "preferred_value": None,
                "data_format": "discrete_text",
                "allowed_values": '["OK"]'
            },
        ]
        for invalid_combination in invalid_combinations:
            dp.data_format = invalid_combination["data_format"]
            dp.allowed_values = invalid_combination["allowed_values"]
            dp.save()

            test_data = {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": 1564489613491,
                        "preferred_value":
                            invalid_combination["preferred_value"],
                        "acceptable_values":
                            [invalid_combination["preferred_value"]]
                    }
                ]
            }
            serializer = DatapointSetpointSerializer(dp, data=test_data)

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
            assert "setpoint" in caught_execption.detail
            exception_detail = str(caught_execption.detail["setpoint"])
            assert "discrete datapoint" in exception_detail

    def test_timestamps_are_validated_against_each_other(self):
        """
        Check that if from_timestamp and to_timestamp is set not None,
        it is validated that to_timestamp is larger.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        # Missing from_timestamp
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": 1564489613492,
                    "to_timestamp": 1564489613491,
                    "preferred_value": "not a number"
                },
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "timestamp must be larger" in exception_detail

    def test_timestamps_are_validated_to_be_numbers(self):
        """
        Check that if from_timestamp and to_timestamp are validated to be
        None or convertable to a number.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": "not 1564489613491",
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "could not be parsed to integer" in exception_detail

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": "not 1564489613491",
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "could not be parsed to integer" in exception_detail

    def test_timestamps_not_in_milliseconds_yield_error(self):
        """
        Check that an error message is yielded if the timestamp is in
        obviously not in milliseconds.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "An actuator datapoint for setpoint testing."
        dp.save()

        # timestamp in seconds.
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613,
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "seems unreasonably low" in exception_detail

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": 1564489613,
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "seems unreasonably low" in exception_detail

        # timestamp in microseconds.
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": 1564489613000000,
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "seems unreasonably high" in exception_detail

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": 1564489613000000,
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ]
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption is not None
        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        exception_detail = str(caught_execption.detail["setpoint"])
        assert "seems unreasonably high" in exception_detail


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
