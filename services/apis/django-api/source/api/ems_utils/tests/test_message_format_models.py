import pytz
import json
from datetime import datetime

from django.conf import settings
from django.db import connection, connections, models
from django.test import TransactionTestCase
from django.db.utils import IntegrityError

from ems_utils.timestamp import datetime_from_timestamp
from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate
from ems_utils.message_format.models import DatapointLastValueTemplate
from ems_utils.message_format.models import DatapointLastScheduleTemplate
from ems_utils.message_format.models import DatapointLastSetpointTemplate


class TestDatapoint(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Generic default values to prevent errors when creating datapoints
        # while violating non empty constraints.
        cls.default_field_values = {"type": "sensor"}

        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models"

        cls.Datapoint = Datapoint
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)

    def tearDown(self):
        """
        Delete all datapoints after each tests to prevent unique constraints
        from short_name.
        """
        self.Datapoint.objects.all().delete()

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

    def test_field_origin_id_exists(self):
        """
        This field is required to match externally managed datapoint metadata.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"origin_id": "1"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_origin_id_is_unique(self):
        """
        origin_id must be unique as we use it to select a single datapoint
        which is updated with the data from the external system.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"origin_id": "1"})

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

    def test_field_short_name_exists(self):
        """
        This field is required for UIs and stuff.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"short_name": "T_1"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_short_name_is_unique(self):
        """
        Short name must be unique if set, to prevent confusion and stuff.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"short_name": "T_1"})

        self.generic_field_value_test(field_values=field_values)
        with self.assertRaises(IntegrityError):
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

    def test_field_type_exists(self):
        """
        This field is an essential information about the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"type": "actuator"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_data_format_exists(self):
        """
        This field is an essential information about the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"data_format": "generic_numeric"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_decription_exists(self):
        """
        This field is an essential information about the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"description": "Sample text"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_allowed_values_exists(self):
        """
        This field carries additional metadata on the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"allowed_values": [1, 2, 3]})

        self.generic_field_value_test(field_values=field_values)

    def test_field_min_value_exists(self):
        """
        This field carries additional metadata on the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"min_value": 10.0})

        self.generic_field_value_test(field_values=field_values)

    def test_field_max_value_exists(self):
        """
        This field carries additional metadata on the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"max_value": 10.0})

        self.generic_field_value_test(field_values=field_values)

    def test_field_unit_exists(self):
        """
        This field carries additional metadata on the datapoint.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"unit": "Mg*m*s^-2"})

        self.generic_field_value_test(field_values=field_values)


class TestDatapointValue(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_2"

        class DatapointValue(DatapointValueTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
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
            'SELECT "datapoint_id", "time", "value", "_value_float", "_value_bool"'
            'FROM "{table_name}" WHERE datapoint_id = %s AND time = %s'
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


class TestDatapointLastValue(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_2_2"

        class DatapointLastValue(DatapointLastValueTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)


class TestDatapointSchedule(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_3"

        class DatapointSchedule(DatapointScheduleTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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
                "to_timestamp": 1564489613491,
                "value": 21,
            },
            {
                "from_timestamp": 1564489613491,
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
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
                "schedule": "A msg at the exact same time as for dp1",
            },
            {
                "datapoint": self.datapoint,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "schedule": [],
            },
            {
                "datapoint": self.datapoint2,
                "time": datetime(2021, 1, 1, 13, 0, 0, tzinfo=pytz.utc),
                "schedule": "A msg at the exact same time as for dp1",
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
                json.dumps("A msg at the exact same time as for dp1"),
            ),
            (
                self.datapoint.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps([]),
            ),
            (
                self.datapoint2.id,
                datetime(2021, 1, 1, 13, 0, 0, **dt_kwargs),
                json.dumps("A msg at the exact same time as for dp1"),
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


class TestDatapointDatapointLastSchedule(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_3_2"

        class DatapointLastSchedule(DatapointLastScheduleTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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
                "to_timestamp": 1564489613491,
                "value": 21,
            },
            {
                "from_timestamp": 1564489613491,
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)


class TestDatapointSetpoint(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_4"

        class DatapointSetpoint(DatapointSetpointTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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
                "to_timestamp": 1564489613491,
                "value": 21,
            },
            {
                "from_timestamp": 1564489613491,
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
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
                "setpoint": "A msg at the exact same time as for dp1",
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
                json.dumps("A msg at the exact same time as for dp1"),
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


class TestDatapointLastSetpoint(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_4_2"

        class DatapointLastSetpoint(DatapointLastSetpointTemplate):
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
            "time": datetime_from_timestamp(1612860152000),
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
                "to_timestamp": 1564489613491,
                "value": 21,
            },
            {
                "from_timestamp": 1564489613491,
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

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"time": ts_datetime})

        self.generic_field_value_test(field_values=field_values)
