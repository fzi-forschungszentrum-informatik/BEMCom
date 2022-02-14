import json
import logging
from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest
from django.conf import settings
from django.db import connection, models
from django.test import TransactionTestCase, RequestFactory
from rest_framework.exceptions import ValidationError

from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import ViewSetWithDatapointFK
from ems_utils.message_format.serializers import DatapointSerializer
from ems_utils.message_format.serializers import DatapointValueSerializer
from ems_utils.timestamp import datetime_from_timestamp


logger = logging.getLogger(__name__)


class TestDatapointViewSetTemplate(TransactionTestCase):
    """
    This view class is verified at the example of the Datapoint Value
    Messages. It should however work for all other derived classes.
    """

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_view_2"

        class DPSerializer(DatapointSerializer):
            class Meta:
                model = Datapoint
                fields = DatapointSerializer.Meta.fields
                read_only_fields = DatapointSerializer.Meta.read_only_fields
                extra_kwargs = DatapointSerializer.Meta.extra_kwargs

        class DatapointViewSet(DatapointViewSetTemplate):
            datapoint_model = Datapoint
            serializer_class = DPSerializer

        cls.Datapoint = Datapoint
        cls.DatapointViewSet = DatapointViewSet

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)

    @classmethod
    def tearDownClass(cls) -> None:
        # Finally, erase the table of the temporary model.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.Datapoint)

    def setUp(self):
        """
        Define some metadata to use during tests.
        """
        self.test_dp_metadata = {
            "type": "sensor",
            "data_format": "generic_numeric",
            "short_name": "test-123",
            "description": "A test datapoint",
            "min_value": 1,
            "max_value": 3,
            "allowed_values": json.dumps([1, "string", True]),
            "unit": "V",
        }

    def tearDown(self):
        """
        Remove all datapoints, so next test starts with empty tables.
        """
        self.Datapoint.objects.all().delete()

    def test_create_stores_datapoint_in_db(self):
        """
        The create method should create a new datapoint and store it in the DB.
        """
        factory = RequestFactory()
        request = factory.post("/datapoint/")
        request.data = self.test_dp_metadata

        response = self.DatapointViewSet().create(request)

        assert response.status_code == 201

        dp = self.Datapoint.objects.get(id=response.data["id"])
        for field, value in self.test_dp_metadata.items():
            assert getattr(dp, field) == value

    def test_create_existing_datatpoint_returns_error(self):
        """
        The create method should create a new datapoint and store it in the DB.
        """
        factory = RequestFactory()
        request = factory.post("/datapoint/")
        request.data = self.test_dp_metadata

        response = self.DatapointViewSet().create(request)

        assert response.status_code == 201

        with pytest.raises(ValidationError):
            response = self.DatapointViewSet().create(request)


class TestViewSetWithDatapointFK(TransactionTestCase):
    """
    This view class is verified at the example of the Datapoint Value
    Messages. It should however work for all other derived classes.
    """

    @classmethod
    def setUpClass(cls):
        # Datapoint model is abstract, hence no table exists. Here we
        # create a concrete model as child of datapoint and create a table
        # on the fly for testing.
        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = "test_message_format_models_view_1"

        class DatapointValue(DatapointValueTemplate):
            class Meta:
                app_label = "test_message_format_models_view_1"

            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(Datapoint, on_delete=models.CASCADE)

        class DatapointValueViewSet(ViewSetWithDatapointFK):
            model = DatapointValue
            datapoint_model = Datapoint
            serializer_class = DatapointValueSerializer
            queryset = DatapointValue.timescale.all()
            create_for_actuators_only = True

        cls.Datapoint = Datapoint
        cls.DatapointValue = DatapointValue
        cls.DatapointValueViewSet = DatapointValueViewSet
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.Datapoint)
            schema_editor.create_model(cls.DatapointValue)

        #  Create a dummy datapoint to be used as foreign key for the msgs.
        cls.datapoint = cls.Datapoint(type="actuator")
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

    def test_list_returns_db_values(self):
        """
        Basic test for list, verifies that the expected values are extracted
        from DB.
        """
        dp_id = self.datapoint.id
        test_values = [
            (datetime(2021, 9, 6, 15, 0, 0, tzinfo=timezone.utc), 1.0),
            (datetime(2021, 9, 6, 15, 7, 30, tzinfo=timezone.utc), 2.0),
            (datetime(2021, 9, 6, 15, 14, 59, tzinfo=timezone.utc), 3.0),
            (datetime(2021, 9, 6, 15, 15, 0, tzinfo=timezone.utc), 4.0),
            (datetime(2021, 9, 6, 15, 22, 30, tzinfo=timezone.utc), 5.0),
            (datetime(2021, 9, 6, 15, 29, 59, tzinfo=timezone.utc), 6.0),
        ]
        for test_time, test_value in test_values:
            dpv = self.DatapointValue(
                datapoint=self.datapoint, time=test_time, value=test_value
            )
            dpv.save()

        factory = RequestFactory()
        request = factory.get("/datapoint/%s/value/" % dp_id)
        response = self.DatapointValueViewSet(request=request).list(
            request, dp_id=dp_id
        )
        actual_data = response.data

        # Expecting left aligned 15 minute blocks.
        expected_dt_1 = datetime(2021, 9, 6, 15, 0, 0, tzinfo=timezone.utc)
        expected_dt_2 = datetime(2021, 9, 6, 15, 15, 0, tzinfo=timezone.utc)
        expected_data = [
            {
                "value": json.dumps(2.0),
                "timestamp": round(expected_dt_1.timestamp() * 1000),
            },
            {
                "value": json.dumps(5.0),
                "timestamp": round(expected_dt_2.timestamp() * 1000),
            },
        ]

        expected_data = []
        for test_time, test_value in test_values:
            expected_data.append(
                {
                    "value": json.dumps(test_value),
                    "timestamp": round(test_time.timestamp() * 1000),
                }
            )

        assert response.status_code == 200
        assert actual_data == expected_data

    @pytest.mark.skipif(
        "timescale" not in settings.DATABASES["default"]["ENGINE"],
        reason="Requires TimescaleDB for correct execution.",
    )
    def test_list_handles_time_buckets(self):
        """
        Checkt that the list method is also able to handle TimescaleQuerySets
        as they are returned when using a filter to generate time buckets.
        This test is necessary as TimescaleQuerySets have a slightly different
        output then normal QuerySets.

        NOTE: This test can only be executed with a TimescaleDB as Backend.
        """
        dp_id = self.datapoint.id
        test_values = [
            (datetime(2021, 9, 6, 15, 0, 0, tzinfo=timezone.utc), 1.0),
            (datetime(2021, 9, 6, 15, 7, 30, tzinfo=timezone.utc), 2.0),
            (datetime(2021, 9, 6, 15, 14, 59, tzinfo=timezone.utc), 3.0),
            (datetime(2021, 9, 6, 15, 15, 0, tzinfo=timezone.utc), 4.0),
            (datetime(2021, 9, 6, 15, 22, 30, tzinfo=timezone.utc), 5.0),
            (datetime(2021, 9, 6, 15, 29, 59, tzinfo=timezone.utc), 6.0),
        ]
        for test_time, test_value in test_values:
            dpv = self.DatapointValue(
                datapoint=self.datapoint, time=test_time, value=test_value
            )
            dpv.save()

        factory = RequestFactory()
        request = factory.get("/datapoint/%s/value/" % dp_id)

        ts_qs = self.DatapointValue.timescale.time_bucket("time", "15 minutes")
        ts_qs = ts_qs.annotate(value=models.Avg("_value_float"))
        # Overload the default ordering from new to old.
        ts_qs = ts_qs.order_by("bucket")
        dpvs = self.DatapointValueViewSet(request=request)
        dpvs.filter_queryset = MagicMock(return_value=ts_qs)

        response = dpvs.list(request, dp_id=dp_id)
        actual_data = response.data

        # Expecting left aligned 15 minute blocks.
        expected_dt_1 = datetime(2021, 9, 6, 15, 0, 0, tzinfo=timezone.utc)
        expected_dt_2 = datetime(2021, 9, 6, 15, 15, 0, tzinfo=timezone.utc)
        expected_data = [
            {
                "value": json.dumps(2.0),
                "timestamp": round(expected_dt_1.timestamp() * 1000),
            },
            {
                "value": json.dumps(5.0),
                "timestamp": round(expected_dt_2.timestamp() * 1000),
            },
        ]

        assert response.status_code == 200
        assert actual_data == expected_data

    @pytest.mark.skipif(
        "timescale" not in settings.DATABASES["default"]["ENGINE"],
        reason="Requires TimescaleDB for correct execution.",
    )
    def test_list_handles_invalid_time_bucket_intervals(self):
        """
        Verify that invalid strings for the time bucket interval are caught.
        """
        dp_id = self.datapoint.id
        dpv = self.DatapointValue(
            datapoint=self.datapoint,
            time=datetime(2021, 9, 6, 15, 0, 0, tzinfo=timezone.utc),
            value=1.0,
        )
        dpv.save()

        factory = RequestFactory()
        request = factory.get("/datapoint/%s/value/" % dp_id)

        # Note the 'no interval' which is not a valid PostgreSQL interval.
        ts_qs = self.DatapointValue.timescale.time_bucket("time", "no interval")
        ts_qs = ts_qs.annotate(value=models.Avg("_value_float"))

        dpvs = self.DatapointValueViewSet(request=request)
        dpvs.filter_queryset = MagicMock(return_value=ts_qs)

        with pytest.raises(ValidationError):
            _ = dpvs.list(request, dp_id=dp_id)

    def test_update_many_writes_to_db(self):
        """
        Verify that we can use the update_many method to write several
        value messages into the DB.
        """
        dp_id = self.datapoint.id
        test_values = [
            (1630409948000, True),
            (1630409948001, False),
            (1630409948002, None),
            (1630409948003, 10),
            (1630409948004, 2.22),
            (1630409948005, "a string!"),
            (1630409948006, ""),
        ]

        test_data = []
        for ts, v in test_values:
            test_data.append({"timestamp": ts, "value": json.dumps(v)})
        factory = RequestFactory()
        request = factory.put("/datapoint/1/value/")
        request.data = test_data

        response = self.DatapointValueViewSet().update_many(
            request, dp_id=dp_id
        )
        assert response.status_code == 200
        assert response.data["msgs_created"] == 7
        assert response.data["msgs_updated"] == 0

        for ts, v in test_values:
            ts_as_dt = datetime_from_timestamp(ts)
            dpv = self.DatapointValue.objects.get(
                datapoint=dp_id, time=ts_as_dt
            )
            assert dpv.value == v

        # Now also check that an posting with an existing timestamp and
        # dp_id will lead to an update.
        test_values = [
            (1630409948005, "a new string!"),
            (1630409948006, "update"),
        ]
        test_data = []
        for ts, v in test_values:
            test_data.append({"timestamp": ts, "value": json.dumps(v)})
        factory = RequestFactory()
        request = factory.put("/datapoint/1/value/")
        request.data = test_data

        response = self.DatapointValueViewSet().update_many(
            request, dp_id=dp_id
        )
        assert response.status_code == 200
        assert response.data["msgs_created"] == 0
        assert response.data["msgs_updated"] == 2

        for ts, v in test_values:
            ts_as_dt = datetime_from_timestamp(ts)
            dpv = self.DatapointValue.objects.get(
                datapoint=dp_id, time=ts_as_dt
            )
            assert dpv.value == v

    def test_update_many_writes_to_db_empty(self):
        """
        Verify that update_many also behaves OK if no data is provided.
        This seems to have crashed the function sometime ago.
        """
        dp_id = self.datapoint.id

        test_data = []
        factory = RequestFactory()
        request = factory.put("/datapoint/1/value/")
        request.data = test_data

        response = self.DatapointValueViewSet().update_many(
            request, dp_id=dp_id
        )
        assert response.status_code == 200
        assert response.data["msgs_created"] == 0
        assert response.data["msgs_updated"] == 0
