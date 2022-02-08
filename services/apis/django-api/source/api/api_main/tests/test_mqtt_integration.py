import os
import json
import time
import logging
from unittest.mock import MagicMock

import pytest

from api_main.models.datapoint import Datapoint
from api_main.models.connector import Connector, ConnectorHeartbeat
from api_main.models.connector import ConnectorLogEntry
from api_main.mqtt_integration import ApiMqttIntegration, MqttToDb
from api_main.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient
from api_main.tests.helpers import connector_factory, datapoint_factory
from ems_utils.timestamp import datetime_from_timestamp


@pytest.fixture(scope="class")
def mqtt_to_db_setup(request, django_db_setup, django_db_blocker):
    """
    Set up fake MQTT Broker and Mqtt2DB for all tests in
    TestConnectorIntegration.

    This is significantly faster then using unittest's setUp and tearDown
    as those are executed for every test function, here only for the class
    as a whole.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)

    # Setup Broker and Integration.
    mqtt_client = fake_client_1()
    mqtt_client.connect("localhost", 1883)
    mqtt_client.loop_start()

    test_connector = connector_factory("test_connector_0")

    mtd = MqttToDb(mqtt_client=fake_client_2, n_mtd_write_threads_overload=1)

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.test_connector = test_connector
    request.cls.mtd = mtd
    yield

    # Remove DB entries, as the restore command below does not seem to work.
    test_connector.delete()

    # Close connections and objects.
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    mtd.disconnect()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures("mqtt_to_db_setup")
class TestMqttToDb:
    """
    Verifies that MqttToDb provides the expected functionality.
    """

    def test_log_msg_received(self):
        """
        Test that a log message received via MQTT is stored in the DB.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
        """
        # Define test data and send to mqtt integration.
        test_log_msg = {
            "timestamp": 1571843907448,
            "msg": "TEest 112233",
            "emitter": "cd54c61d.3064d8",
            "level": 20,
        }
        payload = json.dumps(test_log_msg)
        topic = self.test_connector.mqtt_topic_logs
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while ConnectorLogEntry.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError("Expected Log Entry has not reached DB.")

        # Compare expected and stored data.
        log_msg_db = ConnectorLogEntry.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        timestamp_as_datetime = datetime_from_timestamp(
            test_log_msg["timestamp"]
        )
        assert log_msg_db.timestamp == timestamp_as_datetime
        assert log_msg_db.msg == test_log_msg["msg"]
        assert log_msg_db.emitter == test_log_msg["emitter"]
        assert log_msg_db.level == test_log_msg["level"]

        # Clean up.
        log_msg_db.delete()

    def test_heartbeat_received(self):
        """
        Test that a heartbeat message received via MQTT is stored in the DB.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
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
        while ConnectorHeartbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError("Expected heartbeat has not reached DB.")

        # Compare expected and stored data.
        heartbeat_db = ConnectorHeartbeat.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        last_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat["this_heartbeats_timestamp"]
        )
        next_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat["next_heartbeats_timestamp"]
        )
        assert heartbeat_db.last_heartbeat == last_heartbeat_as_datetime
        assert heartbeat_db.next_heartbeat == next_heartbeat_as_datetime

        # Clean up.
        heartbeat_db.delete()

    def test_available_datapoints_received(self):
        """
        Test that a available_datapoints message received via MQTT is stored
        correctly in the DB.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
        """
        # Numbers will be converted to strings by json.dumps and not converted
        # back by json.loads. Hence use all strings here to prevent type errors
        # while asserting below.
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": 0.122,
                "Channel__P__unit__0": "kW",
            },
            "actuator": {"Channel__P__setpoint__0": True},
        }

        payload = json.dumps(test_available_datapoints)
        topic = self.test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        time.sleep(0.5)
        waited_seconds = 0
        while Datapoint.objects.count() < 3:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected message on available datapoints has not reached "
                    " DB."
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
        ad_db = Datapoint.objects.all()
        actual_rows = []
        for item in ad_db:
            actual_row = (item.type, item.key_in_connector, item.example_value)
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows

        # Clean up.
        for item in ad_db:
            item.delete()

    def test_available_datapoints_updates(self):
        """
        Test that a available_datapoints message received via MQTT updates the
        value in DB instead of appending the existing data.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing.
        """
        # Numbers will be converted to strings by json.dumps and not converted
        # back by json.loads. Hence use all strings here to prevent type errors
        # while asserting below.
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": "0.122",
                "Channel__P__unit__0": "kW",
            },
            "actuator": {"Channel__P__setpoint__0": "0.4"},
        }

        payload = json.dumps(test_available_datapoints)
        topic = self.test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Here comes the update message.
        test_available_datapoints_update = {
            "sensor": {
                "Channel__P__value__0": "0.222",
                "Channel__P__unit__0": "W",
            },
            "actuator": {
                "Channel__P__setpoint__0": "0.5",
                "Channel__M__setpoint__1": "OK",
            },
        }

        payload = json.dumps(test_available_datapoints_update)
        topic = self.test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        time.sleep(0.5)
        waited_seconds = 0
        while Datapoint.objects.count() < 4:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected message on available datapoints has not reached "
                    " DB."
                )

        # Expected rows in DB as tuples of values
        expected_rows = []
        for datapoint_type, d in test_available_datapoints_update.items():
            for datapoint_key, datapoint_example in d.items():
                expected_row = (
                    datapoint_type,
                    datapoint_key,
                    datapoint_example,
                )
                expected_rows.append(expected_row)

        # Actual rows in DB:
        ad_db = Datapoint.objects.all()
        actual_rows = []
        for item in ad_db:
            actual_row = (item.type, item.key_in_connector, item.example_value)
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows

        # Clean up.
        for item in ad_db:
            item.delete()

    def test_datpoint_value_received(self):
        """
        Check that a datapoint value message is handled and stored
        in DB as expected.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
        """
        dp = datapoint_factory(self.test_connector)
        dp.last_value = "The inital value"
        timestamp = 1585092224000
        dp.save()

        # Manually update topics, as this class only tests if
        # MqttToDb works correctly, if handled correctly.
        self.mtd.update_topics()
        self.mtd.update_subscriptions()

        # Define test data and send to mqtt integration.
        update_msg = {"timestamp": 1585092224000, "value": "An update value"}
        payload = json.dumps(update_msg)
        topic = dp.get_mqtt_topics()["value"]
        self.mqtt_client.publish(topic, payload, qos=2)

        # Give the message some time to arrive, as MQTT could be async.
        waited_seconds = 0
        while True:
            dp.refresh_from_db()
            if dp.last_value_message.time is not None:
                break

            time.sleep(0.005)
            waited_seconds += 0.005
            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected datapoint value message has not reached the DB."
                )

        assert dp.last_value_message.value == update_msg["value"]
        expected_ts_as_dt = datetime_from_timestamp(update_msg["timestamp"])
        assert dp.last_value_message.time == expected_ts_as_dt

    def test_datapoint_schedule_received(self):
        """
        Check that a datapoint schedule message is handled and stored
        in DB as expected.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "A actuator datapoint for schedule testing."
        dp.last_schedule = None
        dp.last_schedule_timestamp = None
        dp.save()

        # Manually update topics, as this class only tests if
        # MqttToDb works correctly, if handled correctly.
        self.mtd.update_topics()
        self.mtd.update_subscriptions()

        # Define test data and send to mqtt integration.
        update_schedule = [
            {
                "from_timestamp": None,
                "to_timestamp": 1564489613495,
                "value": "23",
            },
            {
                "from_timestamp": 1564489613495,
                "to_timestamp": None,
                "value": "22",
            },
        ]
        update_msg = {"timestamp": 1564489613491, "schedule": update_schedule}
        payload = json.dumps(update_msg)
        topic = dp.get_mqtt_topics()["schedule"]
        self.mqtt_client.publish(topic, payload, qos=2)

        # Give the message some time to arrive, as MQTT could be async.
        waited_seconds = 0
        while True:
            dp.refresh_from_db()
            if dp.last_schedule_message.time is not None:
                break

            time.sleep(0.005)
            waited_seconds += 0.005
            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected datapoint schedule has not reached the DB."
                )

        assert dp.last_schedule_message.schedule == update_schedule
        expected_ts_as_dt = datetime_from_timestamp(update_msg["timestamp"])
        assert dp.last_schedule_message.time == expected_ts_as_dt

    def test_datapoint_setpoint_received(self):
        """
        Check that a datapoint schedule message is handled and stored
        in DB as expected.

        This test verifies that:
        - __init__ sets up the MQTT connection and calls update_topics as well
          as update_subscriptions.
        - update_topics computes the correct topic for the test message.
        - update_subscriptions subscribes to that topic.
        - on_message handles the incomming MQTT message.
        - message_handle_worker does the expected thing, i.e. store in DB.
        """
        dp = datapoint_factory(self.test_connector, type="actuator")
        dp.description = "A actuator datapoint for schedule testing."
        dp.last_schedule = None
        dp.last_schedule_timestamp = None
        dp.save()

        # Manually update topics, as this class only tests if
        # MqttToDb works correctly, if handled correctly.
        self.mtd.update_topics()
        self.mtd.update_subscriptions()

        # Define test data and send to mqtt integration.
        update_setpoint = [
            {
                "from_timestamp": None,
                "to_timestamp": 1564489613495,
                "preferred_value": "23",
            },
            {
                "from_timestamp": 1564489613495,
                "to_timestamp": None,
                "preferred_value": "22",
            },
        ]
        update_msg = {"timestamp": 1564489613491, "setpoint": update_setpoint}
        payload = json.dumps(update_msg)
        topic = dp.get_mqtt_topics()["setpoint"]
        self.mqtt_client.publish(topic, payload, qos=2)

        # Give the message some time to arrive, as MQTT could be async.
        waited_seconds = 0
        while True:
            dp.refresh_from_db()
            if dp.last_setpoint_message.time is not None:
                break

            time.sleep(0.005)
            waited_seconds += 0.005
            if waited_seconds >= 3:
                raise RuntimeError(
                    "Expected datapoint setpoint has not reached the DB."
                )

        assert dp.last_setpoint_message.setpoint == update_setpoint
        expected_ts_as_dt = datetime_from_timestamp(update_msg["timestamp"])
        assert dp.last_setpoint_message.time == expected_ts_as_dt

    def test_subscribe_to_new_connector(self):
        """
        Test that the topics of the connector added after initialization of
        ConnectorMQTTIntegration are available in the managed topic list as
        well as have been subscribed to.
        """
        # Create a new connector.
        test_connector = connector_factory("test_connector_2")

        # This should trigger adding the topics of the new connector
        # and subscribing to these.
        self.mtd.update_topics_and_subscriptions()

        # Verify topics and subscribtions exist as expected.
        mqtt_topic_attrs = [
            "mqtt_topic_logs",
            "mqtt_topic_heartbeat",
            "mqtt_topic_available_datapoints",
        ]
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics
        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(test_connector, mqtt_topic_attr)
            assert topic in self.mtd.topics
            assert topic in subscribed_topics

        # Clean Up.
        test_connector.delete()

    def test_unsubscribe_from_removed_connector(self):
        """
        Test that the topics of the connector removed after initialization of
        ConnectorMQTTIntegration are no longer available in the managed topic
        list as well as have been unsubscribed from.
        """
        # Create a new connector and make it known to MqttToDB.
        test_connector = connector_factory("test_connector_3")
        self.mtd.update_topics_and_subscriptions()

        mqtt_topic_attrs = [
            "mqtt_topic_logs",
            "mqtt_topic_heartbeat",
            "mqtt_topic_available_datapoints",
        ]
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics

        # Verify that the topics of test_connector_3 are available.
        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(test_connector, mqtt_topic_attr)
            assert topic in self.mtd.topics
            assert topic in subscribed_topics

        # Now delete the test_connector, give the signal some time and
        # verify that the topics are no longer available.
        test_connector.delete()
        self.mtd.update_topics_and_subscriptions()

        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(test_connector, mqtt_topic_attr)
            assert topic not in self.mtd.topics
            assert topic not in subscribed_topics

    def test_log_msg_received_new_connector(self):
        """
        Test that a log message received via MQTT is stored in the DB for a
        connector added after initialization of ConnectorMQTTIntegration.
        """
        # Create a new connector and make it known to MqttToDB.
        test_connector = connector_factory("test_connector_4")
        self.mtd.update_topics_and_subscriptions()

        # Define test data and send to mqtt integration.
        test_log_msg = {
            "timestamp": 1571843907449,
            "msg": "TEest 11223344",
            "emitter": "cd54c61d.3064d8",
            "level": 20,
        }
        payload = json.dumps(test_log_msg)
        topic = test_connector.mqtt_topic_logs
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while ConnectorLogEntry.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError("Expected Log Entry has not reached DB.")

        # Compare expected and stored data.
        log_msg_db = ConnectorLogEntry.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        timestamp_as_datetime = datetime_from_timestamp(
            test_log_msg["timestamp"]
        )
        assert log_msg_db.timestamp == timestamp_as_datetime
        assert log_msg_db.msg == test_log_msg["msg"]
        assert log_msg_db.emitter == test_log_msg["emitter"]
        assert log_msg_db.level == test_log_msg["level"]

        # Clean up.
        log_msg_db.delete()
        test_connector.delete()

    def test_heartbeat_received(self):
        """
        Test that a heartbeat message received via MQTT is stored in the DB
        for a connector added after initialization of ConnectorMQTTIntegration.
        """
        # Create a new connector and make it known to MqttToDB.
        test_connector = connector_factory("test_connector_5")
        self.mtd.update_topics_and_subscriptions()

        test_heartbeat = {
            "this_heartbeats_timestamp": 1571927361262,
            "next_heartbeats_timestamp": 1571927366262,
        }
        payload = json.dumps(test_heartbeat)
        topic = test_connector.mqtt_topic_heartbeat
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while ConnectorHeartbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError("Expected heartbeat has not reached DB.")

        # Compare expected and stored data.
        heartbeat_db = ConnectorHeartbeat.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        last_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat["this_heartbeats_timestamp"]
        )
        next_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat["next_heartbeats_timestamp"]
        )
        assert heartbeat_db.last_heartbeat == last_heartbeat_as_datetime
        assert heartbeat_db.next_heartbeat == next_heartbeat_as_datetime

        # Clean up.
        heartbeat_db.delete()
        test_connector.delete()

    def test_available_datapoints_received(self):
        """
        Test that a available_datapoints message received via MQTT is stored
        correctly in the DB for a connector added after initialization of
        ConnectorMQTTIntegration.
        """
        # Create a new connector and make it known to MqttToDB.
        test_connector = connector_factory("test_connector_6")
        self.mtd.update_topics_and_subscriptions()

        # Numbers will be converted to strings by json.dumps and not converted
        # back by json.loads. Hence use all strings here to prevent type errors
        # while asserting below.
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": "0.522",
                "Channel__P__unit__0": "kW",
            },
            "actuator": {"Channel__P__setpoint__0": "0.5"},
        }

        payload = json.dumps(test_available_datapoints)
        topic = test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        time.sleep(0.5)
        waited_seconds = 0
        dpos = Datapoint.objects
        while dpos.filter(connector=test_connector).count() < 3:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError(
                    "Expected message on available datapoints has not reached "
                    " DB."
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
        ad_db = dpos.filter(connector=test_connector)
        actual_rows = []
        for item in ad_db:
            actual_row = (item.type, item.key_in_connector, item.example_value)
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows

        # Clean up.
        for item in ad_db:
            item.delete()
        test_connector.delete()

    def test_datapoint_message_received(self):
        """
        Test that datapoint messages received via MQTT correctly updates the
        last value and time fields.
        """
        # Create new connector and datapoints and make these known to MqttToDB.
        test_connector = connector_factory("test_connector_7")

        numeric_dp = datapoint_factory(
            test_connector, data_format="generic_numeric"
        )
        text_dp = datapoint_factory(test_connector, data_format="generic_text")
        self.mtd.update_topics_and_subscriptions()

        datapoint_message_numeric = {"value": 13.37, "timestamp": 1571927666222}
        datapoint_message_text = {
            "value": "1337 rulez",
            "timestamp": 1571927666666,
        }

        payload_numeric = json.dumps(datapoint_message_numeric)
        payload_text = json.dumps(datapoint_message_text)
        topic_numeric = numeric_dp.get_mqtt_topics()["value"]
        topic_text = text_dp.get_mqtt_topics()["value"]

        # This is a safeguard from debugging too long into the wrong direction.
        # If this fails the message cannot reach the DB as cmi is not connected
        # to the topic of the two datapoints (yet).
        cmi_subscribed_topics = self.mtd.client.fake_broker.subscribed_topics
        assert topic_text in cmi_subscribed_topics
        assert id(self.mtd.client) in cmi_subscribed_topics[topic_text]
        assert topic_numeric in cmi_subscribed_topics
        assert id(self.mtd.client) in cmi_subscribed_topics[topic_numeric]

        self.mqtt_client.publish(topic_numeric, payload_numeric, qos=2)
        self.mqtt_client.publish(topic_text, payload_text, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while True:
            text_dp.refresh_from_db()
            if text_dp.last_value_message.time is None:
                # That means no update to this datapoint yet.
                time.sleep(0.005)
                waited_seconds += 0.005

                if waited_seconds >= 1:
                    raise RuntimeError(
                        "Expected message on available datapoints has not "
                        "reached DB."
                    )
                continue
            break

        # We expect a string as numeric value as the DB saves everything
        # as strings for simplicity.
        expected_numeric_value = datapoint_message_numeric["value"]
        expected_numeric_timestamp = datapoint_message_numeric["timestamp"]
        expected_numeric_datetime = datetime_from_timestamp(
            expected_numeric_timestamp
        )
        expected_text_value = datapoint_message_text["value"]
        expected_text_timestamp = datapoint_message_text["timestamp"]
        expected_text_datetime = datetime_from_timestamp(
            expected_text_timestamp
        )

        numeric_dp.refresh_from_db()
        actual_numeric_value = numeric_dp.last_value_message.value
        actual_numeric_datetime = numeric_dp.last_value_message.time

        actual_text_value = text_dp.last_value_message.value
        actual_text_datetime = text_dp.last_value_message.time

        assert expected_numeric_value == actual_numeric_value
        assert expected_numeric_datetime == actual_numeric_datetime
        assert expected_text_value == actual_text_value
        assert expected_text_datetime == actual_text_datetime

        # Clean up.
        test_connector.delete()

    def test_datapoint_map_created(self):
        """
        Verify that a datapoint_map message is emitted after a call to
        create_and_send_datapoint_map.

        Also tests that Datapoint.get_mqtt_topic returns the right thing.
        """
        self.mqtt_client.userdata = None

        def on_message(client, userdata, msg):
            """
            Store the received message so we can test it's correctness later.
            """
            client.userdata = msg

        self.mqtt_client.subscribe("test_connector_8/datapoint_map")
        self.mqtt_client.on_message = on_message

        # Add two datapoints that should occur in the datapoint_map
        test_connector = connector_factory("test_connector_8")
        test_datapoint_1 = datapoint_factory(
            connector=test_connector,
            key_in_connector="test_datapoint_map",
            data_format="generic_numeric",
            type="sensor",
        )
        test_datapoint_2 = datapoint_factory(
            connector=test_connector,
            key_in_connector="test_datapoint_map_2",
            data_format="generic_text",
            type="actuator",
        )
        self.mtd.create_and_send_datapoint_map()

        waited_seconds = 0
        while self.mqtt_client.userdata is None:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError(
                    "Expected datapoint map not received via MQTT."
                )

        expected_topic = "test_connector_8/datapoint_map"
        actual_topic = self.mqtt_client.userdata.topic

        dp1_topic = "test_connector_8/messages/%s/value" % str(
            test_datapoint_1.id
        )
        dp2_topic = "test_connector_8/messages/%s/value" % str(
            test_datapoint_2.id
        )

        # Following the datapoint_map format
        expected_payload = {
            "sensor": {test_datapoint_1.key_in_connector: dp1_topic},
            "actuator": {dp2_topic: test_datapoint_2.key_in_connector},
        }

        actual_payload = json.loads(self.mqtt_client.userdata.payload)
        assert actual_payload == expected_payload

        # Clean up.
        test_connector.delete()

    def test_clear_datapoint_map(self):
        """
        Verify that clear_datapoint_map publishes an empty map.
        """
        self.mqtt_client.userdata = None

        def on_message(client, userdata, msg):
            """
            Store the received message so we can test it's correctness later.
            """
            client.userdata = msg

        self.mqtt_client.subscribe("test_connector_9/datapoint_map")
        self.mqtt_client.on_message = on_message

        # Add two datapoints that should not occur in the datapoint_map
        test_connector = connector_factory("test_connector_9")
        test_datapoint_1 = datapoint_factory(
            connector=test_connector,
            key_in_connector="test_datapoint_map",
            data_format="generic_numeric",
            type="sensor",
        )
        test_datapoint_2 = datapoint_factory(
            connector=test_connector,
            key_in_connector="test_datapoint_map_2",
            data_format="generic_text",
            type="actuator",
        )
        # self.mtd.create_and_send_datapoint_map()

        # Now send the clearing map afterwards.
        self.mtd.clear_datapoint_map(connector_id=test_connector.id)

        waited_seconds = 0
        while self.mqtt_client.userdata is None:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 1:
                raise RuntimeError(
                    "Expected datapoint map not received via MQTT."
                )

        expected_payload = {"sensor": {}, "actuator": {}}
        actual_payload = json.loads(self.mqtt_client.userdata.payload)
        assert actual_payload == expected_payload

        # Clean up.
        test_connector.delete()

    def test_rpc_calls_desired_method(self):
        """
        Verify that MQTT messages on RPC topics trigger the desired methods.
        """
        rpc_topics = [
            "django_api/mqtt_to_db/rpc/update_topics_and_subscriptions",
            "django_api/mqtt_to_db/rpc/create_and_send_datapoint_map",
            "django_api/mqtt_to_db/rpc/create_and_send_controlled_datapoints",
            "django_api/mqtt_to_db/rpc/clear_datapoint_map",
        ]
        test_message = {"kwargs": {"foo": "bar"}}
        payload = json.dumps(test_message)

        for topic in rpc_topics:
            # Overload the target method of the RPC call with mock,
            # so we can check if method would have been called.
            target_method_mock = MagicMock()
            target_method_name = topic.split("/")[-1]
            setattr(self.mtd, target_method_name, target_method_mock)

            # Fire the RPC call. If this fails with a real MQTT client, you
            # may want to add some sleep time to allow the message to arrive.
            self.mqtt_client.publish(topic, payload, qos=2, retain=False)

            # Verify the target method has been called with the intended kwargs.
            assert target_method_mock.called
            actual_kwargs = target_method_mock.call_args.kwargs
            expected_kwargs = test_message["kwargs"]
            assert actual_kwargs == expected_kwargs


@pytest.fixture(scope="class")
def allow_db_setup(request, django_db_setup, django_db_blocker):
    """
    Allows DB access for test. This is yet required as the __init__ of
    ConnectorMQTTIntegration will check the DB for topics.
    """
    # Allow access to the Test DB. See:
    # https://pytest-django.readthedocs.io/en/latest/database.html#django-db-blocker
    django_db_blocker.unblock()

    yield

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures("allow_db_setup")
class TestApiMqttIntegration:
    """
    Test that the mechanism of fetching the initialized class instance of
    ConnectorMQTTIntegration from the class object works as expected.
    """

    def setup_method(self, method):
        """
        Generic code executed before every test.
        """
        # Setup MQTT broker and client for tests.
        fake_broker = FakeMQTTBroker()
        fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
        fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)
        mqtt_client = fake_client_1()
        mqtt_client.connect("localhost", 1883)
        mqtt_client.loop_start()

        # Expose to tests.
        self.mqtt_client = mqtt_client
        self.fake_client = fake_client_2

    def teardown_method(self, method):
        """
        Generic code executed after every test.
        """
        # Shut down MQTT connections.
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    def test_get_instance_returns_instance(self):
        """
        Verify that the call to get_instance returns an instance of
        ConnectorMQTTIntegration.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ApiMqttIntegration, "_instance"):
            del ApiMqttIntegration._instance

        initialized_instance = ApiMqttIntegration(mqtt_client=self.fake_client)

        retrieved_instance = ApiMqttIntegration.get_instance()
        assert isinstance(retrieved_instance, ApiMqttIntegration)
        assert id(retrieved_instance) == id(initialized_instance)

    def test_get_instance_returns_singleton_instance(self):
        """
        Verify that repeated calls to __init__ will also return the already
        initialized calls instance, instead of creating new instances.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ApiMqttIntegration, "_instance"):
            del ApiMqttIntegration._instance

        first_initialized_instance = ApiMqttIntegration(
            mqtt_client=self.fake_client
        )

        second_initialized_instance = ApiMqttIntegration(
            mqtt_client=self.fake_client
        )

        assert id(first_initialized_instance) == id(second_initialized_instance)

    def test_get_instance_returns_none_before_init(self):
        """
        Verify that a call to get_instance will return None if the class is
        not initialized yet.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ApiMqttIntegration, "_instance"):
            del ApiMqttIntegration._instance

        not_initialized_instance = ApiMqttIntegration.get_instance()
        assert not_initialized_instance is None

    def test_trigger_update_topics_and_subscriptions_emits_message(self):
        """
        Verify that the trigger_update_topics_and_subscriptions method
        emits the MQTT message expected by MqttToDb.
        """
        # Prepare the test.
        ami = ApiMqttIntegration(mqtt_client=self.fake_client)
        ami.client = MagicMock()

        # Execute the tested method.
        ami.trigger_update_topics_and_subscriptions()

        # Verify that the results are as expected.
        published_messages = ami.client.mock_calls

        assert len(published_messages) == 1
        rcp_call_msg_kwargs = published_messages[0].kwargs

        actual_topic = rcp_call_msg_kwargs["topic"]
        expected_topic = (
            "django_api/mqtt_to_db/rpc/update_topics_and_subscriptions"
        )
        assert actual_topic == expected_topic

        actual_payload = json.loads(rcp_call_msg_kwargs["payload"])
        expected_payload = {"kwargs": {}}
        assert actual_payload == expected_payload

        actual_retain_flag = rcp_call_msg_kwargs["retain"]
        expected_retain_flag = False
        assert actual_retain_flag == expected_retain_flag

        actual_qos_level = rcp_call_msg_kwargs["qos"]
        expected_qos_level = 2
        assert actual_qos_level == expected_qos_level

    def test_trigger_create_and_send_datapoint_map(self):
        """
        Verify that the trigger_create_and_send_datapoint_map method
        emits the MQTT message expected by MqttToDb.
        """
        # Prepare the test.
        ami = ApiMqttIntegration(mqtt_client=self.fake_client)
        ami.client = MagicMock()

        # Execute the tested method.
        ami.trigger_create_and_send_datapoint_map(connector_id=1)

        # Verify that the results are as expected.
        published_messages = ami.client.mock_calls

        assert len(published_messages) == 1
        rcp_call_msg_kwargs = published_messages[0].kwargs

        actual_topic = rcp_call_msg_kwargs["topic"]
        expected_topic = (
            "django_api/mqtt_to_db/rpc/create_and_send_datapoint_map"
        )
        assert actual_topic == expected_topic

        actual_payload = json.loads(rcp_call_msg_kwargs["payload"])
        expected_payload = {"kwargs": {"connector_id": 1}}
        assert actual_payload == expected_payload

        actual_retain_flag = rcp_call_msg_kwargs["retain"]
        expected_retain_flag = False
        assert actual_retain_flag == expected_retain_flag

        actual_qos_level = rcp_call_msg_kwargs["qos"]
        expected_qos_level = 2
        assert actual_qos_level == expected_qos_level

    def test_trigger_create_and_send_controlled_datapoints(self):
        """
        Verify that the trigger_create_and_send_controlled_datapoints method
        emits the MQTT message expected by MqttToDb.
        """
        # Prepare the test.
        ami = ApiMqttIntegration(mqtt_client=self.fake_client)
        ami.client = MagicMock()

        # Execute the tested method.
        ami.trigger_create_and_send_controlled_datapoints(controller_id=2)

        # Verify that the results are as expected.
        published_messages = ami.client.mock_calls

        assert len(published_messages) == 1
        rcp_call_msg_kwargs = published_messages[0].kwargs

        actual_topic = rcp_call_msg_kwargs["topic"]
        expected_topic = (
            "django_api/mqtt_to_db/rpc/create_and_send_controlled_datapoints"
        )
        assert actual_topic == expected_topic

        actual_payload = json.loads(rcp_call_msg_kwargs["payload"])
        expected_payload = {"kwargs": {"controller_id": 2}}
        assert actual_payload == expected_payload

        actual_retain_flag = rcp_call_msg_kwargs["retain"]
        expected_retain_flag = False
        assert actual_retain_flag == expected_retain_flag

        actual_qos_level = rcp_call_msg_kwargs["qos"]
        expected_qos_level = 2
        assert actual_qos_level == expected_qos_level

    def test_trigger_clear_datapoint_map(self):
        """
        Verify that the trigger_clear_datapoint_map method
        emits the MQTT message expected by MqttToDb.
        """
        # Prepare the test.
        ami = ApiMqttIntegration(mqtt_client=self.fake_client)
        ami.client = MagicMock()

        # Execute the tested method.
        ami.trigger_clear_datapoint_map(connector_id=3)

        # Verify that the results are as expected.
        published_messages = ami.client.mock_calls

        assert len(published_messages) == 1
        rcp_call_msg_kwargs = published_messages[0].kwargs

        actual_topic = rcp_call_msg_kwargs["topic"]
        expected_topic = "django_api/mqtt_to_db/rpc/clear_datapoint_map"
        assert actual_topic == expected_topic

        actual_payload = json.loads(rcp_call_msg_kwargs["payload"])
        expected_payload = {"kwargs": {"connector_id": 3}}
        assert actual_payload == expected_payload

        actual_retain_flag = rcp_call_msg_kwargs["retain"]
        expected_retain_flag = False
        assert actual_retain_flag == expected_retain_flag

        actual_qos_level = rcp_call_msg_kwargs["qos"]
        expected_qos_level = 2
        assert actual_qos_level == expected_qos_level
