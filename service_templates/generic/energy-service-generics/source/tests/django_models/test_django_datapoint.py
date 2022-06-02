#!/usr/bin/env python3
"""
Note: This file is called `test_django_datapoint` to prevent name clashes with
`test_datapoint` in the models folder.

TODO: Add tests for `bulk_update_or_create` methods for all three Last* models.
"""
from copy import deepcopy
from datetime import datetime
from datetime import timezone
import json
import pytz

import pytest

try:
    # These are used by the tests, but django is not installed by default.
    from django.conf import settings
    from django.db import connection, models
    from django.test import TransactionTestCase
    from django.db.utils import IntegrityError

    from esg.test.django import GenericDjangoModelTemplateTest
    from esg.test.django import GenericDjangoModelTestMixin

    from esg.django_models.datapoint import DatapointTemplate
    from esg.django_models.datapoint import ValueMessageTemplate  # NOQA
    from esg.django_models.datapoint import ScheduleMessageTemplate  # NOQA
    from esg.django_models.datapoint import SetpointMessageTemplate  # NOQA
    from esg.django_models.datapoint import LastValueMessageTemplate  # NOQA
    from esg.django_models.datapoint import LastScheduleMessageTemplate  # NOQA
    from esg.django_models.datapoint import LastSetpointMessageTemplate  # NOQA

    django_unavailable = False

except ModuleNotFoundError:

    class GenericDjangoModelTemplateTest:
        pass

    class GenericDjangoModelTestMixin:
        pass

    class TransactionTestCase:
        pass

    django_unavailable = True

from esg.test import data as td


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestDatapoint(
    GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin
):
    # These are attributes for the inherited classes.
    model_name = "Datapoint"
    msgs_as_python = [m["Python"] for m in td.datapoints]
    msgs_as_jsonable = [m["JSONable"] for m in td.datapoints]
    invalid_msgs_as_python = []

    # This is specific for this test class.
    default_field_values = {"type": "sensor"}

    @classmethod
    def define_models(cls):
        class Datapoint(DatapointTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

                constraints = [
                    # GOTCHA: This must be copy/pasted to the derived datapoint.
                    # Prevents that a datapoint can be accidently added
                    # multiple times
                    models.UniqueConstraint(
                        fields=["origin", "origin_id"],
                        name="Datapoint unique for origin and origin_id",
                    )
                ]

        return [Datapoint]

    def prepare_messages(self, msgs, msg_name):
        """
        Add foreign keys to positions.
        """
        msgs = deepcopy(msgs)
        for i, msg in enumerate(msgs):
            msg["id"] = i
        return msgs

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint with field_values, and check that the value can be
        restored.
        """
        datapoint = self.Datapoint.objects.create(**field_values)
        datapoint.save()
        # Ensure that we compare to the value that has been stored in DB.
        datapoint.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(datapoint, field)
            self.assertEqual(expected_value, actual_value)

    def test_save_replaces_origin_id_with_None(self):
        """
        The admin would save an empty string which is not unique.
        """
        field_values = self.default_field_values.copy()
        field_values.update({"origin_id": ""})

        datapoint = self.Datapoint.objects.create(**field_values)

        self.assertEqual(datapoint.origin_id, None)

    def test_fields_origin_and_origin_id_unique_together(self):
        """
        origin_id must be unique as we use it to select a single datapoint
        which is updated with the data from the external system.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"origin": "test", "origin_id": "1"})

        self.generic_field_value_test(field_values=field_values)
        with self.assertRaises(IntegrityError):
            self.generic_field_value_test(field_values=field_values)

    def test_field_origin_id_is_not_unique_when_null(self):
        """
        Verify that we can have several datapoints with all null as origin_id
        as this will happen if we add additional datapoints locally while others
        exist that are pushed from the external system.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"origin_id": None})

        self.generic_field_value_test(field_values=field_values)
        self.generic_field_value_test(field_values=field_values)

    def test_field_short_name_is_not_unique_when_null(self):
        """
        If createad automatically, short_name is null, which should not trigger
        the unique constraint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"short_name": None})

        self.generic_field_value_test(field_values=field_values)
        self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestValueMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_2"

        class DatapointValue(ValueMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_2"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointValue = DatapointValue
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointValue)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
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

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_value.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_value, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_value_exists(self):
        """
        Verify that we can store a value.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"value": 1.0})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the values timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def get_raw_values_from_db(self, dp_value_id):
        """
        A utility function that fetches the raw data from the DB.
        """
        query = (
            'SELECT "value", "_value_float", "_value_bool"'
            'FROM "{table_name}" WHERE id = %s'
        ).format(table_name=self.DatapointValue.objects.model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(query, [dp_value_id])
            row = cursor.fetchone()
        return row

    def test_save_will_store_string_on_value_field(self):
        """
        There is an automatic mechanism that stores floats and bool values
        not as strings but as floats/bools to save storage space.
        Verify that the string ends up in the intended table column and
        that all other fields are empty as expected.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.save()

        dp_value.value = "Hello there."
        dp_value.save()

        row = self.get_raw_values_from_db(dp_value_id=dp_value.id)
        actual_value, actual_value_float, actual_value_bool = row

        # Outer quotes because of the JSON field.
        expected_value = '"Hello there."'
        expected_value_float = None
        expected_value_bool = None

        assert actual_value == expected_value
        assert actual_value_float == expected_value_float
        assert actual_value_bool == expected_value_bool

        # Finally also validate that the data can be fetched back from the
        # the value field.
        dp_value.refresh_from_db()
        expected_value = "Hello there."
        actual_value = dp_value.value
        assert actual_value == expected_value

    def test_save_will_store_float_on_value_float_field(self):
        """
        There is an automatic mechanism that stores floats and bool values
        not as strings but as floats/bools to save storage space.
        Verify that the float ends up in the intended table column and
        that all other fields are empty as expected.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.save()

        dp_value.value = 1
        dp_value.save()

        row = self.get_raw_values_from_db(dp_value_id=dp_value.id)
        actual_value, actual_value_float, actual_value_bool = row

        expected_value = None
        expected_value_float = 1
        expected_value_bool = None

        assert actual_value == expected_value
        assert actual_value_float == expected_value_float
        assert actual_value_bool == expected_value_bool

        # Finally also validate that the data can be fetched back from the
        # the value field.
        dp_value.refresh_from_db()
        expected_value = 1
        actual_value = dp_value.value
        assert actual_value == expected_value

    def test_save_will_store_bool_on_value_bool_field(self):
        """
        There is an automatic mechanism that stores floats and bool values
        not as strings but as floats/bools to save storage space.
        Verify that the bool ends up in the intended table column and
        that all other fields are empty as expected.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.save()

        dp_value.value = True
        dp_value.save()

        row = self.get_raw_values_from_db(dp_value_id=dp_value.id)
        actual_value, actual_value_float, actual_value_bool = row

        expected_value = None
        expected_value_float = None
        expected_value_bool = True

        assert actual_value == expected_value
        assert actual_value_float == expected_value_float
        assert actual_value_bool == expected_value_bool

        # Finally also validate that the data can be fetched back from the
        # the value field.
        dp_value.refresh_from_db()
        expected_value = True
        actual_value = dp_value.value
        assert actual_value == expected_value

    def get_raw_values_from_db_by_time_and_dp(self, dp_id, time):
        """
        A utility function that fetches the raw data from the DB.
        """
        query = (
            'SELECT "datapoint_id", "time", "value", "_value_float", '
            '"_value_bool" FROM "{table_name}" WHERE datapoint_id = %s '
            "AND time = %s"
        ).format(table_name=self.DatapointValue.objects.model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(query, [dp_id, time])
            row = cursor.fetchone()
        return row

    def test_bulk_update_or_create_stores_in_db(self):
        """
        Verify that bulk_update_or_create is able to create and update
        data in the DB.
        """
        # These are the Datapoints Msgs that should be updated.
        # We want to have here at least two value msgs from the same datapoint
        # to show that matching and updating msgs works even if several msgs
        # are involved (the matching part). We also want to have msgs from
        # at least to distinct datapoints as we expect the bulk_update_or_create
        # method to distinguish the msgs by datapoints while fetching msgs
        # for updating
        dp_value = self.DatapointValue(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
            value=31.0,
        )
        dp_value.save()
        dp_value2 = self.DatapointValue(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
            value=42,
        )
        dp_value2.save()
        dp_value3 = self.DatapointValue(
            datapoint=self.datapoint2,
            time=datetime(2021, 1, 1, 12, 30, 0, tzinfo=pytz.utc),
            value=False,
        )
        dp_value3.save()

        test_msgs = [
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "value": 32.0,
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "value": "A msg at the exact same time as for dp1",
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 12, 30, 0, tzinfo=pytz.utc),
                "value": True,
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "value": None,
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "value": "A msg at the exact same time as for dp1",
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 14, 0, 0, tzinfo=pytz.utc),
                "value": True,
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 15, 0, 0, tzinfo=pytz.utc),
                "value": "a string",
            },
        ]

        msg_stats = self.DatapointValue.bulk_update_or_create(
            model=self.DatapointValue, msgs=test_msgs
        )

        expected_msgs_created = 4
        actual_msgs_created = msg_stats[0]
        assert actual_msgs_created == expected_msgs_created
        expected_msgs_updated = 3
        actual_msgs_updated = msg_stats[1]
        assert actual_msgs_updated == expected_msgs_updated

        # Apparently SQlite has issues storing timezone for datetimes, while
        # tests fails for PostgreSQL if timezones are not provided like
        # pytz.utc. Maybe this is just because of the hacky style of
        # reading data directly and raw from DB
        db_engine = settings.DATABASES["default"]["ENGINE"]
        if db_engine == "django.db.backends.sqlite3":
            dt_kwargs = {}
        else:
            dt_kwargs = {"tzinfo": pytz.utc}

        # That is "datapoint", "time", "value", "_value_float", "_value_bool"
        all_expected_values = [
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                None,
                32.0,
                None,
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                json.dumps("A msg at the exact same time as for dp1"),
                None,
                None,
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 12, 30, 0, **dt_kwargs),
                None,
                None,
                True,
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps("A msg at the exact same time as for dp1"),
                None,
                None,
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                None,
                None,
                None,
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 14, 0, 0, **dt_kwargs),
                None,
                None,
                True,
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 15, 0, 0, **dt_kwargs),
                json.dumps("a string"),
                None,
                None,
            ),
        ]
        all_actual_values = []
        for expected_value in all_expected_values:
            actual_values = self.get_raw_values_from_db_by_time_and_dp(
                dp_id=expected_value[0], time=expected_value[1]
            )
            all_actual_values.append(actual_values)

        assert all_actual_values == all_expected_values

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.value_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestLastValueMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_2_2"

        class DatapointLastValue(LastValueMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_2_2"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointLastValue = DatapointLastValue
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointLastValue)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointLastValue)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointLastValue.objects.all().delete()

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_value = self.DatapointLastValue.objects.create(**field_values)
        dp_value.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_value.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_value, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_value_exists(self):
        """
        Verify that we can store a value.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"value": 1.0})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the values timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.value_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestScheduleMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_3"

        class DatapointSchedule(ScheduleMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_3"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointSchedule = DatapointSchedule
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointSchedule)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
            "schedule": [],
        }

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

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_schedule = self.DatapointSchedule.objects.create(**field_values)
        dp_schedule.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_schedule.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_schedule, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_schedule_exists(self):
        """
        Verify that we can store a schedule.
        """
        field_values = self.default_field_values.copy()

        schedule = [
            {
                "from_timestamp": None,
                "to_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "value": 21,
            },
            {
                "from_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "to_timestamp": None,
                "value": None,
            },
        ]
        field_values.update({"schedule": schedule})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the schedules timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def get_raw_values_from_db_by_time_and_dp(self, dp_id, time):
        """
        A utility function that fetches the raw data from the DB.
        """
        query = (
            'SELECT "datapoint_id", "time", "schedule"'
            'FROM "{table_name}" WHERE datapoint_id = %s AND time = %s'
        ).format(table_name=self.DatapointSchedule.objects.model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(query, [dp_id, time])
            row = cursor.fetchone()
        return row

    def test_bulk_update_or_create_stores_in_db(self):
        """
        Verify that bulk_update_or_create is able to create and update
        data in the DB.
        """
        # These are the Datapoints Msgs that should be updated.
        dp_schedule = self.DatapointSchedule(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
            schedule=[{"test": 1}],
        )
        dp_schedule.save()

        dp_schedule2 = self.DatapointSchedule(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
            schedule=[{"test": 2}],
        )
        dp_schedule2.save()

        test_msgs = [
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "schedule": [],
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "schedule": [
                    {"value": "A msg at the exact same time as for dp1"}
                ],
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "schedule": [],
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "schedule": [
                    {"value": "A msg at the exact same time as for dp1"}
                ],
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 14, 0, 0, tzinfo=pytz.utc),
                "schedule": [],
            },
        ]

        msg_stats = self.DatapointSchedule.bulk_update_or_create(
            model=self.DatapointSchedule, msgs=test_msgs
        )

        expected_msgs_created = 3
        actual_msgs_created = msg_stats[0]
        assert actual_msgs_created == expected_msgs_created
        expected_msgs_updated = 2
        actual_msgs_updated = msg_stats[1]
        assert actual_msgs_updated == expected_msgs_updated

        # Apparently SQlite has issues storing timezone for datetimes, while
        # tests fails for PostgreSQL if timezones are not provided like
        # pytz.utc. Maybe this is just because of the hacky style of
        # reading data directly and raw from DB
        db_engine = settings.DATABASES["default"]["ENGINE"]
        if db_engine == "django.db.backends.sqlite3":
            dt_kwargs = {}
        else:
            dt_kwargs = {"tzinfo": pytz.utc}

        # That is "datapoint", "time", "schedule"
        all_expected_schedules = [
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                json.dumps(
                    [{"value": "A msg at the exact same time as for dp1"}]
                ),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps(
                    [{"value": "A msg at the exact same time as for dp1"}]
                ),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 14, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
        ]
        all_actual_schedules = []
        for expected_schedule in all_expected_schedules:
            actual_schedule = self.get_raw_values_from_db_by_time_and_dp(
                dp_id=expected_schedule[0], time=expected_schedule[1]
            )
            all_actual_schedules.append(actual_schedule)

        assert all_actual_schedules == all_expected_schedules

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.schedule_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestLastScheduleMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_3_2"

        class DatapointLastSchedule(LastScheduleMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_3_2"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointLastSchedule = DatapointLastSchedule
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointLastSchedule)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
            "schedule": [],
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointLastSchedule)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointLastSchedule.objects.all().delete()

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_schedule = self.DatapointLastSchedule.objects.create(**field_values)
        dp_schedule.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_schedule.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_schedule, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_schedule_exists(self):
        """
        Verify that we can store a schedule.
        """
        field_values = self.default_field_values.copy()

        schedule = [
            {
                "from_timestamp": None,
                "to_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "value": 21,
            },
            {
                "from_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "to_timestamp": None,
                "value": None,
            },
        ]
        field_values.update({"schedule": schedule})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the schedules timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.schedule_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestSetpointMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_4"

        class DatapointSetpoint(SetpointMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_4"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointSetpoint = DatapointSetpoint
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointSetpoint)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
            "setpoint": [],
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointSetpoint)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointSetpoint.objects.all().delete()

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_setpoint = self.DatapointSetpoint.objects.create(**field_values)
        dp_setpoint.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_setpoint.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_setpoint, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_setpoint_exists(self):
        """
        Verify that we can store a setpoint.
        """
        field_values = self.default_field_values.copy()

        setpoint = [
            {
                "from_timestamp": None,
                "to_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "value": 21,
            },
            {
                "from_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "to_timestamp": None,
                "value": None,
            },
        ]
        field_values.update({"setpoint": setpoint})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the setpoints timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def get_raw_values_from_db_by_time_and_dp(self, dp_id, time):
        """
        A utility function that fetches the raw data from the DB.
        """
        query = (
            'SELECT "datapoint_id", "time", "setpoint"'
            'FROM "{table_name}" WHERE datapoint_id = %s AND time = %s'
        ).format(table_name=self.DatapointSetpoint.objects.model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(query, [dp_id, time])
            row = cursor.fetchone()
        return row

    def test_bulk_update_or_create_stores_in_db(self):
        """
        Verify that bulk_update_or_create is able to create and update
        data in the DB.
        """
        # These are the Datapoints Msgs that should be updated.
        dp_setpoint = self.DatapointSetpoint(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
            setpoint=[{"test": 1}],
        )
        dp_setpoint.save()
        dp_setpoint2 = self.DatapointSetpoint(
            datapoint=self.datapoint,
            time=datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
            setpoint=[{"test": 2}],
        )
        dp_setpoint2.save()

        test_msgs = [
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "setpoint": [],
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 12, 0, 0, tzinfo=pytz.utc),
                "setpoint": [
                    {"value": "A msg at the exact same time as for dp1"}
                ],
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "setpoint": [],
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 14, 0, 0, tzinfo=pytz.utc),
                "setpoint": [],
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 15, 0, 0, tzinfo=pytz.utc),
                "setpoint": [],
            },
        ]

        msg_stats = self.DatapointSetpoint.bulk_update_or_create(
            model=self.DatapointSetpoint, msgs=test_msgs
        )

        expected_msgs_created = 3
        actual_msgs_created = msg_stats[0]
        assert actual_msgs_created == expected_msgs_created
        expected_msgs_updated = 2
        actual_msgs_updated = msg_stats[1]
        assert actual_msgs_updated == expected_msgs_updated

        # Apparently SQlite has issues storing timezone for datetimes, while
        # tests fails for PostgreSQL if timezones are not provided like
        # pytz.utc. Maybe this is just because of the hacky style of
        # reading data directly and raw from DB
        db_engine = settings.DATABASES["default"]["ENGINE"]
        if db_engine == "django.db.backends.sqlite3":
            dt_kwargs = {}
        else:
            dt_kwargs = {"tzinfo": pytz.utc}

        # That is "datapoint", "setpoint"
        all_expected_setpoints = [
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 12, 0, 0, **dt_kwargs),
                json.dumps(
                    [{"value": "A msg at the exact same time as for dp1"}]
                ),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 14, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 15, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
        ]
        all_actual_setpoints = []
        for expected_setpoint in all_expected_setpoints:
            actual_setpoint = self.get_raw_values_from_db_by_time_and_dp(
                dp_id=expected_setpoint[0], time=expected_setpoint[1]
            )
            all_actual_setpoints.append(actual_setpoint)

        assert all_actual_setpoints == all_expected_setpoints

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.setpoint_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestLastSetpointMessage(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_4_2"

        class DatapointLastSetpoint(LastSetpointMessageTemplate):
            class Meta:
                app_label = "test_message_format_models_4_2"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        cls.Datapoint = Datapoint
        cls.DatapointLastSetpoint = DatapointLastSetpoint
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointLastSetpoint)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="sensor")
        cls.datapoint.save()
        cls.datapoint2 = cls.Datapoint(type="sensor")
        cls.datapoint2.save()

        # Here are the default field values:
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "time": datetime(2021, 2, 9, 9, 42, 32, tzinfo=timezone.utc),
            "setpoint": [],
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)
            schema_editor.delete_model(cls.DatapointLastSetpoint)

    def tearDown(self):
        """
        Remove the dummy datapoint, so next test starts with empty tables.
        """
        self.DatapointLastSetpoint.objects.all().delete()

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_setpoint = self.DatapointLastSetpoint.objects.create(**field_values)
        dp_setpoint.save()
        # Ensure that we compare to the value that has been stored in DB.
        dp_setpoint.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_setpoint, field)
            self.assertEqual(expected_value, actual_value)

    def test_field_datapoint_exists(self):
        """
        Just check that we can create a new msg with foreign key to
        datapoint.
        """
        field_values = self.default_field_values.copy()

        self.generic_field_value_test(field_values=field_values)

    def test_field_setpoint_exists(self):
        """
        Verify that we can store a setpoint.
        """
        field_values = self.default_field_values.copy()

        setpoint = [
            {
                "from_timestamp": None,
                "to_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "value": 21,
            },
            {
                "from_timestamp": datetime(
                    2022, 2, 22, 2, 52, tzinfo=timezone.utc
                ),
                "to_timestamp": None,
                "value": None,
            },
        ]
        field_values.update({"setpoint": setpoint})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the setpoints timestamp.
        """
        field_values = self.default_field_values.copy()

        ts_datetime = datetime(2021, 8, 1, 0, tzinfo=timezone.utc)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        for valid_example in td.setpoint_messages:
            field_values = self.default_field_values.copy()
            field_values.update(valid_example["Python"])
            self.generic_field_value_test(field_values=field_values)


@pytest.mark.skipif(django_unavailable, reason="requires django and timescale")
class TestForecastMessage(GenericDjangoModelTemplateTest):
    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductRunTemplate
        from esg.django_models.datapoint import DatapointTemplate
        from esg.django_models.datapoint import ForecastMessageTemplate

        class ProductRun(ProductRunTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

            # Disable all relations that are not required for this test.
            _product = None
            plants = None
            product_id = None
            plant_id = None

        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = cls.__name__

        class ForecastMessage(ForecastMessageTemplate):
            class Meta:
                app_label = cls.__name__

            datapoint = models.ForeignKey(
                Datapoint,
                on_delete=models.CASCADE,
                related_name="forecast_messages",
                help_text=(
                    "The datapoint that the forecast message belongs to."
                ),
            )
            product_run = models.ForeignKey(
                ProductRun,
                on_delete=models.CASCADE,
                related_name="forecast_messages",
                help_text=(
                    "The product run that has generated the forecast message."
                ),
            )

        return [ProductRun, Datapoint, ForecastMessage]

    def prepare_messages(self, msgs, msg_name):
        """
        Add foreign keys to positions.
        """
        if msg_name == "msgs_as_python":
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                msg["product_run"] = self.ProductRun(
                    available_at=datetime(2022, 5, 1, 0, tzinfo=timezone.utc),
                    coverage_from=datetime(2022, 5, 1, 0, tzinfo=timezone.utc),
                    coverage_to=datetime(2022, 5, 2, 0, tzinfo=timezone.utc),
                )
                msg["product_run"].save()
                msg["datapoint"] = self.Datapoint(type="Sensor")
                msg["datapoint"].save()
        return msgs

    def generic_field_value_test(self, field_values):
        """
        Create a datapoint value entry with field_values, and check that the
        value can be restored.
        """
        dp_forecast = self.ForecastMessage.objects.create(**field_values)
        dp_forecast.save()
        # Ensure that we compare to the obj that has been stored in DB.
        dp_forecast.refresh_from_db()
        for field in field_values:
            expected_value = field_values[field]
            actual_value = getattr(dp_forecast, field)
            assert expected_value == actual_value

    def test_example_data_can_be_stored(self):
        """
        Verify that we can store the valid examples using the model.
        """
        valid_examples = self.prepare_messages(
            [m["Python"] for m in td.forecast_messages],
            msg_name="msgs_as_python",
        )
        for field_values in valid_examples:
            self.generic_field_value_test(field_values=field_values)

    def test_bulk_update_or_create_stores_in_db(self):
        """
        Verify that bulk_update_or_create is able to create and update
        data in the DB.
        """
        # Create test messages for two tuples of datapoint/product_run
        test_messages_1 = self.prepare_messages(
            [m["Python"] for m in td.forecast_messages],
            msg_name="msgs_as_python",
        )
        test_messages_2 = self.prepare_messages(
            [m["Python"] for m in td.forecast_messages],
            msg_name="msgs_as_python",
        )
        test_messages = []
        test_messages.extend(test_messages_1)
        test_messages.extend(test_messages_2)

        # Create a test message with an altered value so we know later
        # that the update worked.
        test_msg_pre_update = deepcopy(td.forecast_messages[0]["Python"])
        test_msg_pre_update["mean"] = test_msg_pre_update["mean"] - 20.1
        # These are the three fields that identify a unique message.
        test_msg_pre_update["product_run"] = test_messages[0]["product_run"]
        test_msg_pre_update["datapoint"] = test_messages[0]["datapoint"]
        test_msg_pre_update["time"] = test_messages[0]["time"]

        # Verify that the mean value has actually changed!
        assert test_msg_pre_update["mean"] != test_messages[0]["mean"]

        # Store the pre update Message in DB and check it has arrived.
        self.generic_field_value_test(test_msg_pre_update)

        msg_stats = self.ForecastMessage.bulk_update_or_create(
            model=self.ForecastMessage, msgs=test_messages
        )

        expected_msgs_created = len(test_messages) - 1
        actual_msgs_created = msg_stats[0]
        assert actual_msgs_created == expected_msgs_created
        expected_msgs_updated = 1
        actual_msgs_updated = msg_stats[1]
        assert actual_msgs_updated == expected_msgs_updated

        # check that all messages have reached the DB.
        for expected_msg in test_messages:
            actual_msg = self.ForecastMessage.objects.get(
                product_run=expected_msg["product_run"],
                datapoint=expected_msg["datapoint"],
                time=expected_msg["time"],
            )

            for expected_key, expected_value in expected_msg.items():
                actual_value = getattr(actual_msg, expected_key)
                assert actual_value == expected_value
