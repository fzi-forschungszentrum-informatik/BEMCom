import os
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
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
from core.connector_mqtt_integration import ConnectorMQTTIntegration
from core.utils import datetime_from_timestamp


class TestConnectorIntegration(TestCase):
    """
    Test that all messages sent by a standard Connector a saved in the DB.
    """

    @classmethod
    def setUpTestData(self):
        """
        Set up if a message broker exists.
        """
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect('localhost', 1883)

        self.test_connector = models.Connector(
            name='test_connector',
            mqtt_topic_logs='test_connector/logs',
            mqtt_topic_heartbeat='test_connector/heartbeat',
            mqtt_topic_available_datapoints='test_connector/available_datapoints',
            mqtt_topic_datapoint_map='test_connector/datapoint_map',
        )
        self.test_connector.save()

        self.cmi = ConnectorMQTTIntegration()

#    def tearDown(self):
#        self.mqtt_client.disconnect()
#        self.cmi.disconnect()

    def test_log_msg_received(self):
        """
        Test that a log message received via MQTT is stored in the DB.
        """
        # Define test data and send to mqtt integration.
        test_log_msg = {
            "timestamp": 1571843907448,
            "msg": "TEest 112233",
            "emitter": "cd54c61d.3064d8",
            "level": 20
        }
        payload = json.dumps(test_log_msg)
        topic = self.test_connector.mqtt_topic_logs
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while models.ConnectorHearbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError('Expected Log Entry has not reached DB.')

        # Compare expected and stored data.
        log_msg_db = models.ConnectorLogEntry.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        timestamp_as_datetime = datetime_from_timestamp(
            test_log_msg['timestamp']
        )
        assert log_msg_db.timestamp == timestamp_as_datetime
        assert log_msg_db.msg == test_log_msg['msg']
        assert log_msg_db.emitter == test_log_msg['emitter']
        assert log_msg_db.level == test_log_msg['level']

    def test_heartbeat_received(self):
        """
        Test that a heartbeat message received via MQTT is stored in the DB.
        """
        test_heartbeat = {
            "this_heartbeats_timestamp": 1571927361261,
            "next_heartbeats_timestamp": 1571927366261,
        }
        payload = json.dumps(test_heartbeat)
        topic = self.test_connector.mqtt_topic_heartbeat
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while models.ConnectorHearbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError('Expected heartbeat has not reached DB.')

        # Compare expected and stored data.
        heartbeat_db = models.ConnectorHearbeat.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        last_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['this_heartbeats_timestamp']
        )
        next_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['next_heartbeats_timestamp']
        )
        assert heartbeat_db.last_heartbeat == last_heartbeat_as_datetime
        assert heartbeat_db.next_heartbeat == next_heartbeat_as_datetime

    def test_available_datapoints_received(self):
        """
        Test that a available_datapoints message received via MQTT is stored
        correctly in the DB.
        """
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": 0.122,
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": 0.4,
            },
        }

        payload = json.dumps(test_available_datapoints)
        topic = self.test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while models.ConnectorAvailableDatapoints.objects.count() < 3:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError(
                    'Expected message on available datapoints has not reached '
                    ' DB.'
                )

        # Expected rows in DB as tuples of values
        expected_rows = []
        for datapoint_type, d in test_available_datapoints.items():
            for datapoint_key, datapoint_example in d.items():
                expected_row = (
                    datapoint_type,
                    datapoint_key,
                    datapoint_example,
                )
                expected_rows.append(expected_row)

        # Actual rows in DB:
        ad_db = models.ConnectorAvailableDatapoints.objects.all()
        actual_rows = []
        for item in ad_db:
            actual_row = (
                item.datapoint_type,
                item.datapoint_key_in_connector,
                item.datapoint_example_value,
            )
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows


# Execute this, and only this test file if running this file directly.
if __name__ == "__main__":
    filename_no_extension = os.path.splitext(__file__)[0]
    this_file_as_module_str = '.'.join(filename_no_extension.split('/')[-3:])
    execute_from_command_line(['', 'test', this_file_as_module_str, '--keepdb'])
