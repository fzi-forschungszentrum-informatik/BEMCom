import os
import json
import time

import pytest
import paho.mqtt.client as mqtt
from django.test import TransactionTestCase

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    os.environ['DJANGO_SETTINGS_MODULE'] = 'general_configuration.settings'
    os.chdir('../..')
    setup()

from admin_interface import models
from admin_interface.connector_mqtt_integration import ConnectorMQTTIntegration
from admin_interface.utils import datetime_from_timestamp


@pytest.fixture(scope='class')
def connector_integration_setup(request, django_db_setup, django_db_blocker):
    """
    SetUp Fake MQTT Broker and ConnectorMQTTIntegration for all tests in
    TestConnectorIntegration.

    This is significantly faster then using unittest's setUp and tearDown
    as those are executed for every test function, here only for the class
    as a whole.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    # Setup Broker and Integration.
    mqtt_client = mqtt.Client()
    mqtt_client.connect('localhost', 1883)
    mqtt_client.loop_start()

    test_connector = models.Connector(
        name='test_connector',
        mqtt_topic_logs='test_connector/logs',
        mqtt_topic_heartbeat='test_connector/heartbeat',
        mqtt_topic_available_datapoints='test_connector/available_datapoints',
        mqtt_topic_datapoint_map='test_connector/datapoint_map',
    )
    test_connector.save()

    cmi = ConnectorMQTTIntegration(
        mqtt_client=mqtt.Client
    )

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.test_connector = test_connector
    request.cls.cmi = cmi
    yield

    # Close connections and objects.
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    cmi.disconnect()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures('connector_integration_setup')
class TestConnectorIntegration():
    """
    Test that all messages sent by a standard Connector are saved in the DB.
    """

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
        while models.ConnectorLogEntry.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
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

            if waited_seconds >= 3:
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
        # Numbers will be converted to strings by json.dumps and not converted
        # back by json.loads. Hence use all strings here to prevent type errors
        # while asserting below.
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": "0.122",
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": "0.4",
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

            if waited_seconds >= 3:
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


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])

