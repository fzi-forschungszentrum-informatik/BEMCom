from django.test import TransactionTestCase

from api_main.models.connector import Connector
from api_main.models.datapoint import Datapoint
from api_rest_interface.serializers import DatapointSerializer
from api_main.mqtt_integration import ApiMqttIntegration
from api_main.tests.helpers import connector_factory
from api_main.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient


class TestDatapointSerializer(TransactionTestCase):
    @classmethod
    def setUpClass(cls):

        # This is basically just necessary to prevent errors on other
        # parts of the program that expect CMI to be online.
        fake_broker = FakeMQTTBroker()
        fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
        fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)
        ami = ApiMqttIntegration(mqtt_client=fake_client_1)

    def setUp(self):
        test_connector = connector_factory()
        self.test_dp_fields = {
            "connector": test_connector,
            "key_in_connector": "meter_1__channel__0__Channel__0__P",
            "type": "sensor",
            "data_format": "generic_text",
            "short_name": "Heat meter 1 power",
            "description": "Some notes.",
            "min_value": 20.0,
            "max_value": 22.0,
            "allowed_values": None,
            "unit": "W",
        }
        self.test_dp = Datapoint(**self.test_dp_fields)
        self.test_dp.save()

    def tearDown(self):
        self.test_dp.delete()

    def test_expected_dp_fields_in_representation(self):
        """
        Check that the following normal fields are available in representation.
        """
        dp_representation = DatapointSerializer().to_representation(
            instance=self.test_dp
        )

        expected_fields = [
            "key_in_connector",
            "type",
            "data_format",
            "short_name",
            "description",
            "min_value",
            "max_value",
            "allowed_values",
            "unit",
        ]
        for expected_field in expected_fields:
            expected_value = self.test_dp_fields[expected_field]
            actual_value = dp_representation[expected_field]
            assert actual_value == expected_value

    def test_connector_name_in_representation(self):
        """
        The default behaviour of the Model serializer is to represent a
        foreign relation as id. However, these might change, we thus
        prefer the connector name.
        """
        dp_representation = DatapointSerializer().to_representation(
            instance=self.test_dp
        )
        expected_value = {"name": self.test_dp_fields["connector"].name}
        actual_value = dp_representation["connector"]
        assert actual_value == expected_value
