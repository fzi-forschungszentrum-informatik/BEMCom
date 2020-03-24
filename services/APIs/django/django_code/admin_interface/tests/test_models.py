import os
import pytest

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    os.environ['DJANGO_SETTINGS_MODULE'] = 'general_configuration.settings'
    os.chdir('../..')
    setup()

from admin_interface.models.connector import Connector
from admin_interface.models.datapoint import Datapoint
from admin_interface.models.datapoint import GenericTextDatapointAddition
from admin_interface.models.datapoint import GenericNumericDatapointAddition
from admin_interface.connector_mqtt_integration import ConnectorMQTTIntegration
from admin_interface.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient


@pytest.fixture(scope='class')
def datapoint_save_setup(request, django_db_setup, django_db_blocker):
    """
    Setup the environment for the TestDatapointSave class.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    # This is not used in these tests, but CMI must be set up as it will else
    # throw an error during executing the tests.
    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    mqtt_client = fake_client_1()
    mqtt_client.connect('localhost', 1883)
    cmi = ConnectorMQTTIntegration(
        mqtt_client=fake_client_1
    )

    # These are the Models of the Datapoint additions used in the tests.
    dp_addition_models = {
        "numeric": GenericNumericDatapointAddition,
        "text": GenericTextDatapointAddition,
    }

    # We need one connector to create Datapoint objects in the tests
    test_connector = Connector(
        name='test_datapoint_save_connector',
    )
    test_connector.save()

    # Inject objects into test class.
    request.cls.test_connector = test_connector
    request.cls.dp_addition_models = dp_addition_models
    yield

    # Remove DB entries, as the restore command below does not seem to work.
    test_connector.delete()

    # Close connections and objects.
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    cmi.disconnect()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures('datapoint_save_setup')
class TestDatapointSave():

    def test_new_datapoint_numeric(self):
        """
        test case for a new datapoint marked as numeric by default, which
        should usually not happen in reality. However, it should work
        nevertheless.
        """
        # Here the generic test datapoint.
        test_datapoint = Datapoint(
            connector=self.test_connector,
            type="sensor",
            key_in_connector="some_key_in_connector",
            example_value="42"
        )

        # Now the test specific setting
        test_datapoint.data_format = "generic_numeric"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # After save returned we expect the following counts of DB entries
        # with a foreign key to test_datapoint.
        expected_counts = {
            "numeric": 1,
            "text": 0,
        }

        # Evaluate that the expected state is what we get.
        for addition_type in expected_counts:
            expected_count = expected_counts[addition_type]
            addition_model = self.dp_addition_models[addition_type]
            actual_count = addition_model.objects.filter(
                datapoint=test_datapoint,
            ).count()
            assert actual_count == expected_count

        # Finally clean up.
        test_datapoint.delete()

    def test_new_datapoint_text(self):
        """
        test case for a new datapoint marked as text by default, which
        should usually not happen in reality. However, it should work
        nevertheless.
        """
        # Here the generic test datapoint.
        test_datapoint = Datapoint(
            connector=self.test_connector,
            type="sensor",
            key_in_connector="some_key_in_connector",
            example_value="42"
        )

        # Now the test specific setting
        test_datapoint.data_format = "generic_text"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # After save returned we expect the following counts of DB entries
        # with a foreign key to test_datapoint.
        expected_counts = {
            "numeric": 0,
            "text": 1,
        }

        # Evaluate that the expected state is what we get.
        for addition_type in expected_counts:
            expected_count = expected_counts[addition_type]
            addition_model = self.dp_addition_models[addition_type]
            actual_count = addition_model.objects.filter(
                datapoint=test_datapoint,
            ).count()
            assert actual_count == expected_count

        # Finally clean up.
        test_datapoint.delete()

    def test_datapoint_changed_numeric_to_text(self):
        """
        Test case for changing the data_format attribute of a datapoint, which
        should affect the datapoint addition objects too.
        """
        # Here the generic test datapoint.
        test_datapoint = Datapoint(
            connector=self.test_connector,
            type="sensor",
            key_in_connector="some_key_in_connector",
            example_value="42"
        )

        # Now the test specific inital setting
        test_datapoint.data_format = "generic_numeric"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # Now modify the datapooint to a new (test specific) data_format type.
        test_datapoint.data_format = "generic_text"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # After save returned we expect the following counts of DB entries
        # with a foreign key to test_datapoint.
        expected_counts = {
            "numeric": 0,
            "text": 1,
        }

        # Evaluate that the expected state is what we get.
        for addition_type in expected_counts:
            expected_count = expected_counts[addition_type]
            addition_model = self.dp_addition_models[addition_type]
            actual_count = addition_model.objects.filter(
                datapoint=test_datapoint,
            ).count()
            assert actual_count == expected_count

        # Finally clean up.
        test_datapoint.delete()

    def test_datapoint_changed_text_to_numeric(self):
        """
        Test case for changing the data_format attribute of a datapoint, which
        should affect the datapoint addition objects too.
        """
        # Here the generic test datapoint.
        test_datapoint = Datapoint(
            connector=self.test_connector,
            type="sensor",
            key_in_connector="some_key_in_connector",
            example_value="42"
        )

        # Now the test specific inital setting
        test_datapoint.data_format = "generic_text"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # Now modify the datapooint to a new (test specific) data_format type.
        test_datapoint.data_format = "generic_numeric"

        # Call save to trigger the handling of the datapoint additions.
        test_datapoint.save()

        # After save returned we expect the following counts of DB entries
        # with a foreign key to test_datapoint.
        expected_counts = {
            "numeric": 1,
            "text": 0,
        }

        # Evaluate that the expected state is what we get.
        for addition_type in expected_counts:
            expected_count = expected_counts[addition_type]
            addition_model = self.dp_addition_models[addition_type]
            actual_count = addition_model.objects.filter(
                datapoint=test_datapoint,
            ).count()
            assert actual_count == expected_count

        # Finally clean up.
        test_datapoint.delete()

if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
