import json
import logging

from django.db import connection, models
from django.test import TransactionTestCase

from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate
from ems_utils.message_format.serializers import DatapointValueSerializer
from ems_utils.message_format.serializers import DatapointScheduleSerializer
from ems_utils.message_format.serializers import DatapointSetpointSerializer
from ems_utils.timestamp import datetime_from_timestamp, timestamp_utc_now


logger = logging.getLogger(__name__)


class TestDatapointValueSerializer(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_5"
        class DatapointValue(DatapointValueTemplate):
            class Meta:
                app_label="test_message_format_models_5"
            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(
                Datapoint,
                on_delete=models.CASCADE,
            )
        cls.Datapoint = Datapoint
        cls.DatapointValue = DatapointValue
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointValue)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "timestamp": datetime_from_timestamp(1612860152000),
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointValue)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointValue.objects.all().delete()

    def test_to_representation(self):
        """
        Check that a value message is serialzed as expected.
        """
        expected_data = {
            "value": "Test Value",
            "timestamp": timestamp_utc_now(),
        }

        field_values = self.default_field_values.copy()
        field_values.update({
            "value": expected_data["value"],
            "timestamp": datetime_from_timestamp(expected_data["timestamp"])
        })
        dp_value = self.DatapointValue.objects.create(**field_values)

        serializer = DatapointValueSerializer(dp_value)
        assert serializer.data == expected_data

    def test_to_representation_for_none(self):
        """
        Check that a value message is serialzed as expected if the value is
        None.
        """
        expected_data = {
            "value": None,
            "timestamp": timestamp_utc_now(),
        }

        field_values = self.default_field_values.copy()
        field_values.update({
            "value": expected_data["value"],
            "timestamp": datetime_from_timestamp(expected_data["timestamp"])
        })
        dp_value = self.DatapointValue.objects.create(**field_values)

        serializer = DatapointValueSerializer(dp_value)
        assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that timestamp and value fields must be provided.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)

        test_data = json.loads('{}')
        serializer = DatapointValueSerializer(dp_value, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "value" in caught_execption.detail
        assert "timestamp" in caught_execption.detail

    def test_numeric_value_validated(self):
        """
        Check that for numeric data_format values, only numeric values are
        accepted.
        """
        dp = self.datapoint
        dp.allowed_values = ["not a number"]
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
                "value": "not a number",
                "timestamp": timestamp_utc_now(),
            }
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

            test_data = {
                "value": "not a number",
                "timestamp": timestamp_utc_now(),
            }
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
        dp = self.datapoint
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
                "value": valid_combination["value"],
                "timestamp": timestamp_utc_now(),
            }
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
            dp.save()

            test_data = {
                "value": invalid_combination["value"],
                "timestamp": timestamp_utc_now(),
            }
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
        dp = self.datapoint
        dp.description = "A sensor datapoint for testing"
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {
                "value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": [1.0, 2.0, 3.0]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 2, 3]
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["OK", "Done"]
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": [None, "Nope"]
            },
        ]
        for valid_combination in valid_combinations:
            dp.data_format = valid_combination["data_format"]
            dp.allowed_values = valid_combination["allowed_values"]
            dp.save()

            test_data = {
                "value": valid_combination["value"],
                "timestamp": timestamp_utc_now(),
            }

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
                "allowed_values": [1.0, 3.0]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 3]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": []
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["NotOK", "OK "]
            },
            {
                "value": "",
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
            },
        ]
        for invalid_combination in invalid_combinations:
            dp.data_format = invalid_combination["data_format"]
            dp.allowed_values = invalid_combination["allowed_values"]
            dp.save()

            test_data = {
                "value": invalid_combination["value"],
                "timestamp": timestamp_utc_now(),
            }
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


    def test_timestamp_validated(self):
        """
        Check that the serialzer doesn't accept unresonable low or high
        timestamp values, nor strings.'
        """
        wrong_timestamps = [
            timestamp_utc_now() + 2e11,
            timestamp_utc_now() - 2e11,
            "asdkajsdkajs"
        ]

        for timestamp in wrong_timestamps:

            test_data = {
                "value": None,
                "timestamp": timestamp,
            }

            serializer = DatapointValueSerializer(
                self.datapoint, data=test_data
            )
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "timestamp" in caught_execption.detail


class TestDatapointScheduleSerializer(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_6"
        class DatapointSchedule(DatapointScheduleTemplate):
            class Meta:
                app_label="test_message_format_models_6"
            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(
                Datapoint,
                on_delete=models.CASCADE,
            )
        cls.Datapoint = Datapoint
        cls.DatapointSchedule = DatapointSchedule
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointSchedule)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()

        # Here are the default field values:
        cls.default_field_values = {"datapoint": cls.datapoint}

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointSchedule)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointSchedule.objects.all().delete()


    def test_to_representation(self):
        """
        Check that a schedule message is serialized as expected.
        """
        expected_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": timestamp_utc_now() + 1000,
                    'value': 21
                },
                {
                    "from_timestamp": timestamp_utc_now() + 1000,
                    "to_timestamp": None,
                    'value': None
                }
            ],
            "timestamp": timestamp_utc_now(),
        }

        field_values = self.default_field_values.copy()
        field_values.update({
            "schedule": expected_data["schedule"],
            "timestamp": datetime_from_timestamp(expected_data["timestamp"])
        })
        dp_schedule = self.DatapointSchedule.objects.create(**field_values)

        serializer = DatapointScheduleSerializer(dp_schedule)
        assert serializer.data == expected_data

    #
    # # Deactivated. None is currently not defined as a valid schedule
    #
    # def test_to_representation_for_none(self):
    #     """
    #     Check that a schedule message is serialized as expected if the
    #     schedule is None.
    #     """
    #     expected_data = {
    #         "schedule": None,
    #         "timestamp": timestamp_utc_now(),
    #     }
    #
    #     field_values = self.default_field_values.copy()
    #     field_values.update({
    #         "schedule": expected_data["schedule"],
    #         "timestamp": datetime_from_timestamp(expected_data["timestamp"])
    #     })
    #     dp_schedule = self.DatapointSchedule.objects.create(**field_values)
    #
    #     serializer = DatapointScheduleSerializer(dp_schedule)
    #     assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that schedule and timestamp fields must be given.
        """
        dp = self.datapoint

        test_data = {}
        serializer = DatapointScheduleSerializer(dp, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "schedule" in caught_execption.detail
        assert "timestamp" in caught_execption.detail

    def test_timestamp_validated(self):
        """
        Check that the serialzer doesn't accept unresonable low or high
        timestamp values, nor strings.'
        """
        wrong_timestamps = [
            timestamp_utc_now() + 2e11,
            timestamp_utc_now() - 2e11,
            "asdkajsdkajs"
        ]

        for timestamp in wrong_timestamps:

            test_data = {
                "schedule": None,
                "timestamp": timestamp,
            }

            serializer = DatapointScheduleSerializer(
                self.datapoint, data=test_data
            )
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "timestamp" in caught_execption.detail

    def test_schedule_validated_as_correct_json_or_null(self):
        """
        Check that the schedule is validated to be a parsable as json.
        """
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        # First this is correct json.
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": timestamp_utc_now() + 1000,
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
        }
        serializer = DatapointScheduleSerializer(dp, data=test_data)
        assert serializer.is_valid(raise_exception=True)

        #
        # # This is currently not a valid schedule anymore.
        #
        # # This is also ok.
        # test_data = {
        #     "schedule": None,
        #     "timestamp": timestamp_utc_now(),
        # }
        # serializer = DatapointScheduleSerializer(dp, data=test_data)
        # assert serializer.is_valid(raise_exception=True)

    def test_schedule_validated_as_list(self):
        """
        Check that the schedule is validated to be a list.
        """
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        # This is correct json but not a list of schedule items.
        test_data = {
            "schedule": {"Nope": 1},
            "timestamp": timestamp_utc_now(),
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

    def test_schedule_items_validated_as_dict(self):
        """
        Check that the schedule items are validated to be dicts.
        """
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        # This is correct json but not a list of schedule items.
        test_data = {
            "schedule": ["Nope", 1],
            "timestamp": timestamp_utc_now(),
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

    def test_schedule_items_validated_for_expected_keys(self):
        """
        Check that the schedule items are validated to contain only the
        expected keys and nothing else.
        """
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        # Missing from_timestamp
        test_data = {
            "schedule": [
                {
                    "to_timestamp": timestamp_utc_now() + 1000,
                    "value": "not a number",
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "value": "not a number",
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "to_timestamp": timestamp_utc_now() + 1000,
                }
            ],
            "timestamp": timestamp_utc_now(),
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

        # This test doesn't work if the serializer fields are explicitly
        # defined. Here the serializer simply ignores additional keys.
        #
        # # Additional value
        # test_data = {
        #     "schedule": [
        #         {
        #             "from_timestamp": None,
        #             "to_timestamp": timestamp_utc_now() + 1000,
        #             "value": "not a number",
        #             "not_expected_field": "Should fail"
        #         }
        #     ],
        #     "timestamp": timestamp_utc_now(),
        # }
        # serializer = DatapointScheduleSerializer(dp, data=test_data)
        # caught_execption = None
        # try:
        #     serializer.is_valid(raise_exception=True)
        # except Exception as e:
        #     caught_execption = e

        # assert caught_execption is not None
        # assert caught_execption.status_code == 400
        # assert "schedule" in caught_execption.detail

    def test_numeric_value_of_schedule_validated(self):
        """
        Check that for numeric data_format values, only numeric values are
        accepted within schedules.
        """
        dp = self.datapoint
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": "not a number"
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": "not a number"
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": valid_combination["value"]
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": invalid_combination["value"]
                    },
                ],
                "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
        dp.data_format = "continuous_numeric"
        dp.save()

        valid_combinations = [
            {
                "value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": [1.0, 2.0, 3.0]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 2, 3]
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["OK", "Done"]
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": [None, "Nope"]
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": valid_combination["value"]
                    },
                ],
                "timestamp": timestamp_utc_now(),
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
                "allowed_values": [1.0, 3.0]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 3]
            },
            {
                "value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": []
            },
            {
                "value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["NotOK", "OK "]
            },
            {
                "value": "",
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
            },
            {
                "value": None,
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "value": valid_combination["value"]
                    },
                ],
                "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        test_data = {
            "schedule": [
                {
                    "from_timestamp": timestamp_utc_now(),
                    "to_timestamp": timestamp_utc_now() - 1000,
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": "not 1564489613491",
                    "value": 'not a number'
                }
            ],
            "timestamp": timestamp_utc_now(),
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
        assert "integer" in exception_detail

        test_data = {
            "schedule": [
                {
                    "from_timestamp": "not 1564489613491",
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
        assert "integer" in exception_detail

    def test_timestamps_not_in_milliseconds_yield_error(self):
        """
        Check that an error message is yielded if the timestamp is in
        obviously not in milliseconds.
        """
        dp = self.datapoint
        dp.data_format = "generic_text"
        dp.save()

        # timestamp in seconds.
        test_data = {
            "schedule": [
                {
                    "from_timestamp": None,
                    "to_timestamp": round(timestamp_utc_now() / 1000),
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "from_timestamp": round(timestamp_utc_now() / 1000),
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "to_timestamp": round(timestamp_utc_now() * 1000),
                    "value": "not a number'"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "from_timestamp": round(timestamp_utc_now() * 1000),
                    "to_timestamp": None,
                    "value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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


class TestDatapointSetpointSerializer(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_7"
        class DatapointSetpoint(DatapointSetpointTemplate):
            class Meta:
                app_label="test_message_format_models_7"
            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(
                Datapoint,
                on_delete=models.CASCADE,
            )
        cls.Datapoint = Datapoint
        cls.DatapointSetpoint = DatapointSetpoint
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointSetpoint)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()

        # Here are the default field values:
        cls.default_field_values = {"datapoint": cls.datapoint}

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointSetpoint)

    def setUp(self):
        """
        Reset datapoint metadata after each test, to prevent unexpected
        validation errors due to value checking and stuff.
        """
        self.datapoint.data_format = "generic_text"
        self.datapoint.save()

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointSetpoint.objects.all().delete()

    def test_to_representation(self):

        """
        Check that a setpoint message is serialized as expected.
        """
        expected_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": timestamp_utc_now() + 1000,
                    'preferred_value': 21,
                    'acceptable_values': [20.5, 21, 21.5],

                },
                {
                    "from_timestamp": timestamp_utc_now() + 1000,
                    "to_timestamp": None,
                    'preferred_value': None,
                    'acceptable_values': [None]
                }
            ],
            "timestamp": timestamp_utc_now(),
        }

        field_values = self.default_field_values.copy()
        field_values.update({
            "setpoint": expected_data["setpoint"],
            "timestamp": datetime_from_timestamp(expected_data["timestamp"])
        })
        dp_schedule = self.DatapointSetpoint.objects.create(**field_values)

        serializer = DatapointSetpointSerializer(dp_schedule)
        assert serializer.data == expected_data
    #
    # # Deactivated. None is currently not defined as a valid setpoint
    #
    # def test_to_representation_for_none(self):
    #
    #     """
    #     Check that a setpoint message is serialized as expected if the
    #     setpoint is None.
    #     """
    #     expected_data = {
    #         "setpoint": None,
    #         "timestamp": timestamp_utc_now(),
    #     }
    #
    #     field_values = self.default_field_values.copy()
    #     field_values.update({
    #         "setpoint": expected_data["setpoint"],
    #         "timestamp": datetime_from_timestamp(expected_data["timestamp"])
    #     })
    #     dp_schedule = self.DatapointSetpoint.objects.create(**field_values)
    #
    #     serializer = DatapointSetpointSerializer(dp_schedule)
    #     assert serializer.data == expected_data

    def test_required_fields(self):
        """
        Check that setpoint and timestamp fields must be given.
        """
        dp = self.datapoint

        test_data = {}
        serializer = DatapointSetpointSerializer(dp, data=test_data)

        caught_execption = None
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            caught_execption = e

        assert caught_execption.status_code == 400
        assert "setpoint" in caught_execption.detail
        assert "timestamp" in caught_execption.detail

    def test_timestamp_validated(self):
        """
        Check that the serialzer doesn't accept unresonable low or high
        timestamp values, nor strings.'
        """
        wrong_timestamps = [
            timestamp_utc_now() + 2e11,
            timestamp_utc_now() - 2e11,
            "asdkajsdkajs"
        ]

        for timestamp in wrong_timestamps:

            test_data = {
                "setpoint": None,
                "timestamp": timestamp,
            }

            serializer = DatapointSetpointSerializer(
                self.datapoint, data=test_data
            )
            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                caught_execption = e

            assert caught_execption is not None
            assert caught_execption.status_code == 400
            assert "timestamp" in caught_execption.detail

    def test_setpoint_validated_as_correct_json_or_null(self):
        """
        Check that the setpoint is validated to be a parsable as json.
        """
        dp = self.datapoint

        # First this is correct json.
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": timestamp_utc_now() + 1000,
                    'preferred_value': 'not a number'
                },
            ],
            "timestamp": timestamp_utc_now(),
        }
        serializer = DatapointSetpointSerializer(dp, data=test_data)
        assert serializer.is_valid()

        #
        # # This is currently not a valid setpoint anymore.
        #
        # # This is also ok.
        # test_data = {
        #     "setpoint": None,
        #     "timestamp": timestamp_utc_now(),
        # }
        # serializer = DatapointSetpointSerializer(dp, data=test_data)
        # assert serializer.is_valid()

    def test_setpoint_validated_as_list(self):
        """
        Check that the setpoint is validated to be a list.
        """
        dp = self.datapoint

        # This is correct json but not a list of setpoint items.
        test_data = {
            "setpoint": {"Nope": 1},
            "timestamp": timestamp_utc_now(),
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

    def test_setpoint_items_validated_as_dict(self):
        """
        Check that the setpoint items are validated to be dicts.
        """
        dp = self.datapoint

        # This is correct json but not a list of setpoint items.
        test_data = {
            "setpoint": ["Nope", 1],
            "timestamp": timestamp_utc_now(),
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

    def test_setpoint_items_validated_for_expected_keys(self):
        """
        Check that the setpoint items are validated to contain only the
        expected keys and nothing else.
        """
        dp = self.datapoint

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
        #
        # This is not used, see below.
        #
        # # Here a list of keys which will be tested as extra keys, that should
        # # be refused. The keys that are valid for other data_formats are of
        # # course especially interesting.
        # nvk = ["no_valid_key"]

        # unexpected_keys_per_data_format = {
        #     "generic_numeric": nvk + only_con_keys + only_dis_keys,
        #     "continuous_numeric": nvk + only_dis_keys,
        #     "discrete_numeric": nvk + only_con_keys,
        #     "generic_text": nvk + only_con_keys + only_dis_keys,
        #     "discrete_text": nvk + only_con_keys,
        # }

        # Here the dummy values for all fields used above.
        setpoint_all_fields = {
            "from_timestamp": None,
            "to_timestamp": timestamp_utc_now() + 1000,
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
                    "setpoint": [setpoint],
                    "timestamp": timestamp_utc_now(),
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

        #
        # This does not work as the SetpointItem class will not pick up
        # any unexpected fields.
        #
        # # Now construct test cases to verify that additional unexpected
        # # keys are rejected.
        # for data_format in unexpected_keys_per_data_format:
        #     dp.data_format = data_format
        #     dp.save()
        #     unexpected_keys = unexpected_keys_per_data_format[data_format]
        #     required_keys = required_keys_per_data_format[data_format]

        #     setpoint = {}
        #     for unexpected_key in unexpected_keys:
        #         for key in required_keys:
        #             setpoint[key] = setpoint_all_fields[key]

        #         setpoint[unexpected_key] = setpoint_all_fields[unexpected_key]

        #         test_data = {
        #             "setpoint": [setpoint],
        #             "timestamp": timestamp_utc_now(),
        #         }

        #         serializer = DatapointSetpointSerializer(dp, data=test_data)
        #         caught_execption = None
        #         try:
        #             serializer.is_valid(raise_exception=True)
        #             logger.error(
        #                 "Failed to identify unexpected key (%s) while "
        #                 " validating setpoint data for data_format (%s)" %
        #                 (unexpected_key, data_format)
        #             )
        #         except Exception as e:
        #             caught_execption = e

        #         assert caught_execption is not None
        #         assert caught_execption.status_code == 400
        #         assert "setpoint" in caught_execption.detail
        #         exception_detail = str(caught_execption.detail["setpoint"])
        #         assert "Found unexpected key" in exception_detail

    def test_numeric_value_of_setpoint_validated(self):
        """
        Check that for numeric data_formats, only numeric preferred_values are
        accepted within setpoints.
        """
        dp = self.datapoint
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
            "to_timestamp": timestamp_utc_now() + 1000,
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
                "setpoint": [setpoint],
                "timestamp": timestamp_utc_now(),
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
                "setpoint": [setpoint],
                "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "preferred_value":
                            valid_combination["preferred_value"],
                        "min_value": None,
                        "max_value": None
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "preferred_value":
                            invalid_combination["preferred_value"],
                        "min_value": None,
                        "max_value": None
                    },
                ],
                "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint

        valid_combinations = [
            {
                "preferred_value": 2.0,
                "data_format": "discrete_numeric",
                "allowed_values": [1.0, 2.0, 3.0]
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 2, 3]
            },
            {
                "preferred_value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["OK", "Done"]
            },
            {
                "preferred_value": None,
                "data_format": "discrete_text",
                "allowed_values": [None, "Nope"]
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "preferred_value":
                            valid_combination["preferred_value"],
                        "acceptable_values":
                            [valid_combination["preferred_value"]]
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
                "allowed_values": [1.0, 3.0]
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": [1, 3]
            },
            {
                "preferred_value": 2,
                "data_format": "discrete_numeric",
                "allowed_values": []
            },
            {
                "preferred_value": "OK",
                "data_format": "discrete_text",
                "allowed_values": ["NotOK", "OK "]
            },
            {
                "preferred_value": "",
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
            },
            {
                "preferred_value": None,
                "data_format": "discrete_text",
                "allowed_values": ["OK"]
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
                        "to_timestamp": timestamp_utc_now() + 1000,
                        "preferred_value":
                            invalid_combination["preferred_value"],
                        "acceptable_values":
                            [invalid_combination["preferred_value"]]
                    }
                ],
                "timestamp": timestamp_utc_now(),
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
            assert "preferred_value" in exception_detail

    def test_timestamps_are_validated_against_each_other(self):
        """
        Check that if from_timestamp and to_timestamp is set not None,
        it is validated that to_timestamp is larger.
        """
        dp = self.datapoint
        dp.save()

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": timestamp_utc_now(),
                    "to_timestamp": timestamp_utc_now() - 1000,
                    "preferred_value": "not a number"
                },
            ],
            "timestamp": timestamp_utc_now(),
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
        dp = self.datapoint
        dp.save()

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": "not 1564489613491",
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
        assert "integer" in exception_detail

        test_data = {
            "setpoint": [
                {
                    "from_timestamp": "not 1564489613491",
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
        assert "integer" in exception_detail

    def test_timestamps_not_in_milliseconds_yield_error(self):
        """
        Check that an error message is yielded if the timestamp is in
        obviously not in milliseconds.
        """
        dp = self.datapoint
        dp.save()

        # timestamp in seconds.
        test_data = {
            "setpoint": [
                {
                    "from_timestamp": None,
                    "to_timestamp": round(timestamp_utc_now() / 1000),
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "from_timestamp": round(timestamp_utc_now() / 1000),
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "to_timestamp": round(timestamp_utc_now() * 1000),
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
                    "from_timestamp": round(timestamp_utc_now() * 1000),
                    "to_timestamp": None,
                    "preferred_value": "not a number"
                }
            ],
            "timestamp": timestamp_utc_now(),
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
