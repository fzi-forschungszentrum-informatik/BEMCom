from django.db import connection, models
from django.test import TransactionTestCase
from django.db.utils import IntegrityError

from ems_utils.timestamp import datetime_from_timestamp
from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate

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
                app_label="test_message_format_models"
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


    def test_field_last_value_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

        field_values.update({"last_value": "3.12345"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_last_value_timestamp_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"last_value_timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)


    def test_field_last_setpoint_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

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
        field_values.update({"last_setpoint": last_setpoint})

        self.generic_field_value_test(field_values=field_values)

    def test_field_last_setpoint_timestamp_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"last_setpoint_timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_field_last_schedule_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

        last_schedule = [
            {
                'from_timestamp': None,
                'to_timestamp': 1564489613491,
                'value': 21
            },
            {
                'from_timestamp': 1564489613491,
                'to_timestamp': None,
                'value': None
            }
        ]
        field_values.update({"last_schedule": last_schedule})

        self.generic_field_value_test(field_values=field_values)

    def test_field_last_schedule_timestamp_exists(self):
        """
        This field stores datapoint payload.
        """
        field_values = self.default_field_values.copy()

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"last_schedule_timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)


class TestDatapointValue(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_2"
        class DatapointValue(DatapointValueTemplate):
            class Meta:
                app_label="test_message_format_models_2"
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
            "timestamp": datetime_from_timestamp(1612860152000)
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

        field_values.update({"value": "1.0"})

        self.generic_field_value_test(field_values=field_values)

    def test_field_timestamp_exists(self):
        """
        Verify that we can store the values timestamp.
        """
        field_values = self.default_field_values.copy()

        ts = 1596240000000
        ts_datetime = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update({"timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_save_stores_as_last_value(self):
        """
        The model should save the latest value/timestamp in datapoint too.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is no newer msg available that would prevent saving.
        self.datapoint.last_value = None
        self.datapoint.last_value_timestamp = None
        self.datapoint.save()

        expected_value = "3.14159"
        ts = 1596240000000
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"value": expected_value, "timestamp": expected_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_value = self.datapoint.last_value
        actual_timestamp = self.datapoint.last_value_timestamp

        self.assertEqual(actual_value, expected_value)
        self.assertEqual(actual_timestamp, expected_timestamp)

    def test_save_wont_overwrite_newer_value(self):
        """
        Don't save the value/timestamp to datapoint if it is older then
        the msg stored there.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is a newer msg available that will prevent saving.
        expected_value = "3.14159"
        self.datapoint.last_value = expected_value
        ts = 1596240000000
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        self.datapoint.last_value_timestamp = expected_timestamp
        self.datapoint.save()

        older_value = "-2.0"
        ts = 1200000000000
        older_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"value": older_value, "timestamp": older_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_value = self.datapoint.last_value
        actual_timestamp = self.datapoint.last_value_timestamp

        self.assertEqual(actual_value, expected_value)
        self.assertEqual(actual_timestamp, expected_timestamp)

    def test_save_will_store_float_as_float(self):
        """
        There is an automatic mechanism that stores float values not as strings
        but as floats to save storage space. It's hard to check here if the
        values are really stored that way in DB, but we assume so if the
        floats have been parsed.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.save()

        dp_value.value = "1"
        dp_value.save()
        dp_value.refresh_from_db()

        expected_value = "1.0"
        dp_value.refresh_from_db()
        actual_value = dp_value.value

        assert actual_value == expected_value

    def test_value_float_also_populated(self):
        """
        Float values are made available as float (not string) under the
        value_float field. Check this is the case.
        """
        field_values = self.default_field_values.copy()
        dp_value = self.DatapointValue.objects.create(**field_values)
        dp_value.value = "21.2"
        dp_value.save()

        dp_value.refresh_from_db()
        expected_value = 21.2
        actual_value = dp_value.value_float

        assert actual_value == expected_value

class TestDatapointSchedule(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_3"
        class DatapointSchedule(DatapointScheduleTemplate):
            class Meta:
                app_label="test_message_format_models_3"
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
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "timestamp": datetime_from_timestamp(1612860152000),
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
                'from_timestamp': None,
                'to_timestamp': 1564489613491,
                'value': 21
            },
            {
                'from_timestamp': 1564489613491,
                'to_timestamp': None,
                'value': None
            }
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
        field_values.update({"timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_save_stores_as_last_schedule(self):
        """
        The model should save the latest schedule/timestamp in datapoint too.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is no newer msg available that would prevent saving.
        self.datapoint.last_schedule = None
        self.datapoint.last_schedule_timestamp = None
        self.datapoint.save()

        expected_schedule = [
            {
                'from_timestamp': None,
                'to_timestamp': 1564489613492,
                'value': 21
            },
            {
                'from_timestamp': 1564489613492,
                'to_timestamp': None,
                'value': None
            }
        ]
        ts = 1596230000001
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"schedule": expected_schedule, "timestamp": expected_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_schedule = self.datapoint.last_schedule
        actual_timestamp = self.datapoint.last_schedule_timestamp

        self.assertEqual(actual_schedule, expected_schedule)
        self.assertEqual(actual_timestamp, expected_timestamp)

    def test_save_wont_overwrite_newer_schedule(self):
        """
        Don't save the value/timestamp to datapoint if it is older then
        the msg stored there.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is a newer msg available that will prevent saving.
        expected_schedule = [
            {
                'from_timestamp': None,
                'to_timestamp': 1564489613492,
                'value': 21
            },
            {
                'from_timestamp': 1564489613492,
                'to_timestamp': None,
                'value': None
            }
        ]
        self.datapoint.last_schedule = expected_schedule
        ts = 1596220000000
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        self.datapoint.last_schedule_timestamp = expected_timestamp
        self.datapoint.save()

        older_schedule = []
        ts = 1200000000000
        older_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"schedule": older_schedule, "timestamp": older_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_schedule = self.datapoint.last_schedule
        actual_timestamp = self.datapoint.last_schedule_timestamp

        self.assertEqual(actual_schedule, expected_schedule)
        self.assertEqual(actual_timestamp, expected_timestamp)


class TestDatapointSetpoint(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label="test_message_format_models_4"
        class DatapointSetpoint(DatapointSetpointTemplate):
            class Meta:
                app_label="test_message_format_models_4"
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
        cls.default_field_values = {
            "datapoint": cls.datapoint,
            "timestamp": datetime_from_timestamp(1612860152000),
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
                'from_timestamp': None,
                'to_timestamp': 1564489613491,
                'value': 21
            },
            {
                'from_timestamp': 1564489613491,
                'to_timestamp': None,
                'value': None
            }
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
        field_values.update({"timestamp": ts_datetime})

        self.generic_field_value_test(field_values=field_values)

    def test_save_stores_as_last_setpoint(self):
        """
        The model should save the latest setpoint/timestamp in datapoint too.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is no newer msg available that would prevent saving.
        self.datapoint.last_setpoint = None
        self.datapoint.last_setpoint_timestamp = None
        self.datapoint.save()

        expected_setpoint = [
            {
                'from_timestamp': None,
                'to_timestamp': 1564489613492,
                'value': 21
            },
            {
                'from_timestamp': 1564489613492,
                'to_timestamp': None,
                'value': None
            }
        ]
        ts = 1596220000001
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"setpoint": expected_setpoint, "timestamp": expected_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_setpoint = self.datapoint.last_setpoint
        actual_timestamp = self.datapoint.last_setpoint_timestamp

        self.assertEqual(actual_setpoint, expected_setpoint)
        self.assertEqual(actual_timestamp, expected_timestamp)

    def test_save_wont_overwrite_newer_setpoint(self):
        """
        Don't save the value/timestamp to datapoint if it is older then
        the msg stored there.
        """
        field_values = self.default_field_values.copy()

        # Ensure there is a newer msg available that will prevent saving.
        expected_setpoint = [
            {
                'from_timestamp': None,
                'to_timestamp': 1564489613492,
                'value': 21
            },
            {
                'from_timestamp': 1564489613492,
                'to_timestamp': None,
                'value': None
            }
        ]
        self.datapoint.last_setpoint = expected_setpoint
        ts = 1596220000000
        expected_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        self.datapoint.last_setpoint_timestamp = expected_timestamp
        self.datapoint.save()

        older_setpoint = []
        ts = 1200000000000
        older_timestamp = datetime_from_timestamp(ts, tz_aware=True)
        field_values.update(
            {"setpoint": older_setpoint, "timestamp": older_timestamp}
        )

        self.generic_field_value_test(field_values=field_values)
        self.datapoint.refresh_from_db()
        actual_setpoint = self.datapoint.last_setpoint
        actual_timestamp = self.datapoint.last_setpoint_timestamp

        self.assertEqual(actual_setpoint, expected_setpoint)
        self.assertEqual(actual_timestamp, expected_timestamp)
