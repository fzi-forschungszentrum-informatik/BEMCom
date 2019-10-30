import os

from django.test import TestCase

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    from django.core.management import execute_from_command_line
    os.environ['DJANGO_SETTINGS_MODULE'] = 'manager.settings'
    os.chdir('../..')
    setup()

from core import models


class TestModelOnDelete(TestCase):

    def setUp(self):
        """
        This also tests that all attributes are set up correctly.
        """
        self.connector = models.Connector.objects.create(
            name='Test connector',
            mqtt_topic_logs='Stuff',
            mqtt_topic_heartbeat='More stuff',
            mqtt_topic_new_datapoints='Topic stuff',
            mqtt_topic_datapoint_map='Map Stuff',
            mqtt_topic_messages_prefix='Prefix stuff'
        )

        self.device_type = models.DeviceType.objects.create(
            name='Test device type'
        )

        self.device = models.Device.objects.create(
            name='Test device',
            connector=self.connector,
            device_type=self.device_type,
            is_virtual=False,
            x=0.1,
            y=0.2,
            z=0.3
        )

        self.unit = models.Unit.objects.create(
            name='Test unit'
        )

        self.datapoint = models.Datapoint.objects.create(
            device=self.device,
            unit=self.unit
        )

    def test_no_dataloss_on_unit_delete(self):
        """
        After deleting a unit the datapoint should still exist.
        """
        self.unit.delete()
        assert models.Datapoint.objects.all()

    def test_stuff(self):
        c1 = models.Connector.objects.all()[0]
        assert c1.name == 'Test connector'


# Execute this, and only this test file if running this file directly.
if __name__ == "__main__":
    filename_no_extension = os.path.splitext(__file__)[0]
    this_file_as_module_str = '.'.join(filename_no_extension.split('/')[-3:])
    execute_from_command_line(['', 'test', this_file_as_module_str])
