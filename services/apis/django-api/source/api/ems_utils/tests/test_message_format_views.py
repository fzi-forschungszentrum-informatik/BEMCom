import json
import logging

import pytest
from django.db import connection, models
from django.test import TransactionTestCase, RequestFactory
from rest_framework.exceptions import ValidationError

from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import ViewSetWithDatapointFK
from ems_utils.message_format.serializers import DatapointSerializer
from ems_utils.message_format.serializers import DatapointValueSerializer
from ems_utils.timestamp import datetime_from_timestamp, timestamp_utc_now


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
                app_label="test_message_format_models_view_2"

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
            "unit": "V"
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
                app_label="test_message_format_models_view_1"
        class DatapointValue(DatapointValueTemplate):
            class Meta:
                app_label="test_message_format_models_view_1"
            # The datapoint foreign key must be overwritten as it points
            # to the abstract datapoint model by default.
            datapoint = models.ForeignKey(
                Datapoint,
                on_delete=models.CASCADE,
            )
        class DatapointValueViewSet(ViewSetWithDatapointFK):
            model = DatapointValue
            datapoint_model = Datapoint
            serializer_class = DatapointValueSerializer
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
        test_values = []

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
