import os
import json
import time

import pytest

# Sets path and django such that we can execute this file stand alone and
# develop interactive too.
if __name__ == "__main__":
    from django import setup
    os.environ['DJANGO_SETTINGS_MODULE'] = 'general_configuration.settings'
    os.chdir('../..')
    setup()

from main.models.datapoint import Datapoint
from main.models.connector import Connector, ConnectorHeartbeat
from main.models.connector import ConnectorLogEntry
from main.connector_mqtt_integration import ConnectorMQTTIntegration
from main.utils import datetime_from_timestamp
from main.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient

# TODO This is devl stuff, Remove.
import logging
logger = logging.getLogger(__name__)


def connector_factory(connector_name=None):
    """
    Create a test connector in DB.

    This function is not thread save and may produce errors if other code
    inserts objects in models.Connector in parallel.

    Arguments:
    ----------
    connector_name: string or None
        If string uses this name as connector name. Else will automatically
        generate a name that is "test_connector_" + id of Connector. Be aware
        that mqtt topics are automatically generated from the name and that
        name and mqtt_topics must be unique.

    Returns:
    --------
    test_connector: Connector object
        A dummy Connector for tests.
    """
    if connector_name is None:
        next_id = Connector.objects.count() + 1
        connector_name = "test_connector_" + str(next_id)

    test_connector = Connector(
        name=connector_name,
    )
    test_connector.save()

    return test_connector


def datapoint_factory(connector, key_in_connector=None, data_format="generic_text",
                      type="sensor"):
    """
    Create a dummy datapoint in DB.

    This function is not thread save and may produce errors if other code
    inserts objects in Datapoint in parallel.

    Arguments:
    ----------
    connector: Connector object
        The connector the datapoint belongs to.
    key_in_connector:
        If string uses it's value as key_in_connector. Else will automatically
        generate a key that is "key__in__connector__" + id of Datapoint.
    data_format: str
        See Datapoint.
    type: str
        See Datapoint.

    Returns:
    --------
    test_datapoint: Datapoint object
        A dummy datapoint for tests.
    """
    if key_in_connector is None:
        next_id = Datapoint.objects.count() + 1
        key_in_connector = "key__in__connector__" + str(next_id)

    test_datapoint = Datapoint(
        connector=connector,
        key_in_connector=key_in_connector,
        data_format=data_format,
        type=type,
        is_active=True,
    )
    test_datapoint.save()

    return test_datapoint


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

    fake_broker = FakeMQTTBroker()
    fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
    fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)

    # Setup Broker and Integration.
    mqtt_client = fake_client_1()
    mqtt_client.connect('localhost', 1883)
    mqtt_client.loop_start()

    # Delete _instance as tests above might have created an instance.
    if hasattr(ConnectorMQTTIntegration, "_instance"):
        del ConnectorMQTTIntegration._instance

    # This would throw an error as the post_save signal is fired but
    # the ConnectorMQTTIntegration instance is not ready yet.
    # However, the signal receiver ignores this one special connector_name.
    special_connector_name = (
        "the_only_connector_name_that_won't_fire_the_signal"
    )
    test_connector = connector_factory(special_connector_name)

    cmi = ConnectorMQTTIntegration(
        mqtt_client=fake_client_2
    )

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.test_connector = test_connector
    request.cls.cmi = cmi
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


@pytest.mark.usefixtures('connector_integration_setup')
class TestConnectorIntegration():
    """
    Test that all messages sent by a standard Connector are saved in the DB.

    This tests effectively:
        __init__ : i.e. that the client is set up correctly.
        update_topics : At least the first execution of it.
        update_subscriptions : At least the first run of the function.
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
        while ConnectorLogEntry.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError('Expected Log Entry has not reached DB.')

        # Compare expected and stored data.
        log_msg_db = ConnectorLogEntry.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        timestamp_as_datetime = datetime_from_timestamp(
            test_log_msg['timestamp']
        )
        assert log_msg_db.timestamp == timestamp_as_datetime
        assert log_msg_db.msg == test_log_msg['msg']
        assert log_msg_db.emitter == test_log_msg['emitter']
        assert log_msg_db.level == test_log_msg['level']

        # Clean up.
        log_msg_db.delete()

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
        while ConnectorHeartbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError('Expected heartbeat has not reached DB.')

        # Compare expected and stored data.
        heartbeat_db = ConnectorHeartbeat.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        last_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['this_heartbeats_timestamp']
        )
        next_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['next_heartbeats_timestamp']
        )
        assert heartbeat_db.last_heartbeat == last_heartbeat_as_datetime
        assert heartbeat_db.next_heartbeat == next_heartbeat_as_datetime

        # Clean up.
        heartbeat_db.delete()

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
        while Datapoint.objects.count() < 3:
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
        ad_db = Datapoint.objects.all()
        actual_rows = []
        for item in ad_db:
            actual_row = (
                item.type,
                item.key_in_connector,
                item.example_value,
            )
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

        # Here comes the update message.
        test_available_datapoints_update = {
            "sensor": {
                "Channel__P__value__0": "0.222",
                "Channel__P__unit__0": "W",
            },
            "actuator": {
                "Channel__P__setpoint__0": "0.5",
                "Channel__M__setpoint__1": "OK"
            },
        }

        payload = json.dumps(test_available_datapoints_update)
        topic = self.test_connector.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while Datapoint.objects.count() < 4:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError(
                    'Expected message on available datapoints has not reached '
                    ' DB.'
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
            actual_row = (
                item.type,
                item.key_in_connector,
                item.example_value,
            )
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows

        # Clean up.
        for item in ad_db:
            item.delete()


@pytest.fixture(scope='class')
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


@pytest.mark.usefixtures('allow_db_setup')
class TestGetInstance():
    """
    Test that the mechanism of fetching the initialized class instance of
    ConnectorMQTTIntegration from the class object works as expected.
    """

    def test_instance_is_returned(self):
        """
        Verify that the call to get_instance returns an instance of
        ConnectorMQTTIntegration.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ConnectorMQTTIntegration, "_instance"):
            del ConnectorMQTTIntegration._instance

        fake_broker = FakeMQTTBroker()
        fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)

        # Setup Broker and Integration.
        mqtt_client = fake_client_1()
        mqtt_client.connect('localhost', 1883)
        mqtt_client.loop_start()

        initialized_instance = ConnectorMQTTIntegration(
            mqtt_client=fake_client_1
        )

        retrieved_instance = ConnectorMQTTIntegration.get_instance()
        assert isinstance(retrieved_instance, ConnectorMQTTIntegration)
        assert id(retrieved_instance) == id(initialized_instance)

    def test_singleton(self):
        """
        Verify that repeated calls to __init__ will also return the already
        initialized calls instance, instead of creating new instances.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ConnectorMQTTIntegration, "_instance"):
            del ConnectorMQTTIntegration._instance

        fake_broker = FakeMQTTBroker()
        fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)

        # Setup Broker and Integration.
        mqtt_client = fake_client_1()
        mqtt_client.connect('localhost', 1883)
        mqtt_client.loop_start()

        first_initialized_instance = ConnectorMQTTIntegration(
            mqtt_client=fake_client_1
        )

        second_initialized_instance = ConnectorMQTTIntegration(
            mqtt_client=fake_client_1
        )

        assert (
            id(first_initialized_instance) ==
            id(second_initialized_instance)
        )

    def test_returns_none_before_init(self):
        """
        Verify that a call to get_instance will return None if the class is
        not initialized yet.
        """
        # Delete _instance as tests above might have created an instance.
        if hasattr(ConnectorMQTTIntegration, "_instance"):
            del ConnectorMQTTIntegration._instance

        not_initialized_instance = ConnectorMQTTIntegration.get_instance()
        assert not_initialized_instance is None


@pytest.fixture(scope='class')
def update_subscription_setup(request, django_db_setup, django_db_blocker):
    """
    SetUp Fake MQTT Broker and ConnectorMQTTIntegration for all tests in
    TestUpdateSubscription.

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
    mqtt_client.connect('localhost', 1883)
    mqtt_client.loop_start()

    # Delete _instance as tests above might have created an instance.
    if hasattr(ConnectorMQTTIntegration, "_instance"):
        del ConnectorMQTTIntegration._instance

    # This would throw an error as the post_save signal is fired but
    # the ConnectorMQTTIntegration instance is not ready yet.
    # However, the signal receiver ignores this one special connector_name.
    special_connector_name = (
        "the_only_connector_name_that_won't_fire_the_signal"
    )
    test_connector = connector_factory(special_connector_name)

    cmi = ConnectorMQTTIntegration(
        mqtt_client=fake_client_2
    )

    # Create additional connector and remove the first one to simulate
    # changes after ConnectorMQTTIntegration has been inizialized.
    test_connector_2 = connector_factory("test_connector_2")
    test_connector_3 = connector_factory("test_connector_3")
    test_connector_4 = connector_factory("test_connector_4")
    test_connector_5 = connector_factory("test_connector_5")

    # Create some test datapoints used for checking that normal datapoint
    # messages will be handled correctly too.
    numeric_datapoint = datapoint_factory(
        test_connector_5,
        data_format="generic_numeric"
    )
    text_datapoint = datapoint_factory(
        test_connector_5,
        data_format="generic_text"
    )

    # Give django a seconds to receive the signal and call update_topcis
    # as well as update_subscriptions.
    time.sleep(0.5)

    # Inject objects into test class.
    request.cls.mqtt_client = mqtt_client
    request.cls.test_connector = test_connector
    request.cls.test_connector_2 = test_connector_2
    request.cls.test_connector_3 = test_connector_3
    request.cls.test_connector_4 = test_connector_4
    request.cls.cmi = cmi
    request.cls.numeric_datapoint = numeric_datapoint
    request.cls.text_datapoint = text_datapoint
    yield

    # Close connections and objects.
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    cmi.disconnect()

    # Remove access to DB.
    django_db_blocker.block()
    django_db_blocker.restore()


@pytest.mark.usefixtures('update_subscription_setup')
class TestUpdateSubscription():
    """
    Tests for the handling of changed Connector entries after the
    initialization of ConnectorMQTTIntegration.

    This tests effectively the functions `update_topics` and
    `update_subscriptions` and their handling of changes after the first.
    initialization of ConnectorMQTTIntegration.

    Furhtermore all tests require a correct signal handling of post_save
    signals for the Connector model. Hence, if all tests of this class fail,
    this might be the reason.

    # TODO: There are missing tests for the case if a connector is deleted.
            I.e. there should be no more handling of messages.
    """

    def test_subscribe_to_new_connector(self):
        """
        Test that the topics of the connector added after initialization of
        ConnectorMQTTIntegration are available in the managed topic list as
        well as have been subscribed to.
        """
        mqtt_topic_attrs = [
            "mqtt_topic_logs",
            "mqtt_topic_heartbeat",
            "mqtt_topic_available_datapoints",
        ]
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics

        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(self.test_connector_2, mqtt_topic_attr)
            assert topic in self.cmi.userdata["topics"]
            assert topic in subscribed_topics

    def test_unsubscribe_from_removed_connector(self):
        """
        Test that the topics of the connector removed after initialization of
        ConnectorMQTTIntegration are no longer available in the managed topic
        list as well as have been unsubscribed from.
        """
        mqtt_topic_attrs = [
            "mqtt_topic_logs",
            "mqtt_topic_heartbeat",
            "mqtt_topic_available_datapoints",
        ]
        subscribed_topics = self.mqtt_client.fake_broker.subscribed_topics

        # Verify that the topics of test_connector_3 are available.
        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(self.test_connector_3, mqtt_topic_attr)
            assert topic in self.cmi.userdata["topics"]
            assert topic in subscribed_topics

        # Now delete the test_connector, give the signal some time and
        # verify that the topics are no longer available.
        self.test_connector_3.delete()
        time.sleep(0.5)

        for mqtt_topic_attr in mqtt_topic_attrs:
            topic = getattr(self.test_connector_3, mqtt_topic_attr)
            assert topic not in self.cmi.userdata["topics"]
            assert topic not in subscribed_topics

    def test_log_msg_received_new_connector(self):
        """
        Test that a log message received via MQTT is stored in the DB for a
        connector added after initialization of ConnectorMQTTIntegration.
        """
        # Define test data and send to mqtt integration.
        test_log_msg = {
            "timestamp": 1571843907449,
            "msg": "TEest 11223344",
            "emitter": "cd54c61d.3064d8",
            "level": 20
        }
        payload = json.dumps(test_log_msg)
        topic = self.test_connector_2.mqtt_topic_logs
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while ConnectorLogEntry.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError('Expected Log Entry has not reached DB.')

        # Compare expected and stored data.
        log_msg_db = ConnectorLogEntry.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        timestamp_as_datetime = datetime_from_timestamp(
            test_log_msg['timestamp']
        )
        assert log_msg_db.timestamp == timestamp_as_datetime
        assert log_msg_db.msg == test_log_msg['msg']
        assert log_msg_db.emitter == test_log_msg['emitter']
        assert log_msg_db.level == test_log_msg['level']

        # Clean up.
        log_msg_db.delete()

    def test_heartbeat_received(self):
        """
        Test that a heartbeat message received via MQTT is stored in the DB
        for a connector added after initialization of ConnectorMQTTIntegration.
        """
        test_heartbeat = {
            "this_heartbeats_timestamp": 1571927361262,
            "next_heartbeats_timestamp": 1571927366262,
        }
        payload = json.dumps(test_heartbeat)
        topic = self.test_connector_2.mqtt_topic_heartbeat
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        while ConnectorHeartbeat.objects.count() == 0:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError('Expected heartbeat has not reached DB.')

        # Compare expected and stored data.
        heartbeat_db = ConnectorHeartbeat.objects.first()

        # DB stores timestamp as datetime objects, convert here accordingly.
        last_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['this_heartbeats_timestamp']
        )
        next_heartbeat_as_datetime = datetime_from_timestamp(
            test_heartbeat['next_heartbeats_timestamp']
        )
        assert heartbeat_db.last_heartbeat == last_heartbeat_as_datetime
        assert heartbeat_db.next_heartbeat == next_heartbeat_as_datetime

        # Clean up.
        heartbeat_db.delete()

    def test_available_datapoints_received(self):
        """
        Test that a available_datapoints message received via MQTT is stored
        correctly in the DB for a connector added after initialization of
        ConnectorMQTTIntegration.
        """
        # Numbers will be converted to strings by json.dumps and not converted
        # back by json.loads. Hence use all strings here to prevent type errors
        # while asserting below.
        test_available_datapoints = {
            "sensor": {
                "Channel__P__value__0": "0.522",
                "Channel__P__unit__0": "kW",
            },
            "actuator": {
                "Channel__P__setpoint__0": "0.5",
            },
        }

        payload = json.dumps(test_available_datapoints)
        topic = self.test_connector_2.mqtt_topic_available_datapoints
        self.mqtt_client.publish(topic, payload, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        dpos = Datapoint.objects
        while dpos.filter(connector=self.test_connector_2).count() < 3:
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
        ad_db = dpos.filter(connector=self.test_connector_2)
        actual_rows = []
        for item in ad_db:
            actual_row = (
                item.type,
                item.key_in_connector,
                item.example_value,
            )
            actual_rows.append(actual_row)

        # Finnaly check if the rows are identical.
        assert expected_rows == actual_rows

        # Clean up.
        for item in ad_db:
            item.delete()

    def test_datapoint_message_received(self):
        """
        Test that datapoint messages received via MQTT correctly update the
        Addition models of Datapoint.

        TODO: Also test that datapoint maps always contain sensor and actuator
        key.
        """
        text_dp = self.text_datapoint
        numeric_dp = self.numeric_datapoint
        numeric_dp.save()

        datapoint_message_numeric = {
            "value": 13.37,
            "timestamp": 1571927666222,
        }
        datapoint_message_text = {
            "value": "1337 rulez",
            "timestamp": 1571927666666,
        }

        payload_numeric = json.dumps(datapoint_message_numeric)
        payload_text = json.dumps(datapoint_message_text)
        topic_numeric = numeric_dp.get_mqtt_topic()
        topic_text = text_dp.get_mqtt_topic()
        self.mqtt_client.publish(topic_numeric, payload_numeric, qos=2)
        self.mqtt_client.publish(topic_text, payload_text, qos=2)

        # Wait for the data to reach the DB
        waited_seconds = 0
        datapointaddition = text_dp.get_addition_object()
        while True:

            if datapointaddition.last_timestamp is None:
                # That means no update to this datapoint yet.
                time.sleep(0.005)
                waited_seconds += 0.005

                if waited_seconds >= 3:
                    raise RuntimeError(
                        'Expected message on available datapoints has not '
                        'reached DB.'
                    )
                continue
            break

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

        datapointaddition = numeric_dp.get_addition_object()
        actual_numeric_value = datapointaddition.last_value
        actual_numeric_datetime = datapointaddition.last_timestamp

        datapointaddition = text_dp.get_addition_object()
        actual_text_value = datapointaddition.last_value
        actual_text_datetime = datapointaddition.last_timestamp

        assert expected_numeric_value == actual_numeric_value
        assert expected_numeric_datetime == actual_numeric_datetime
        assert expected_text_value == actual_text_value
        assert expected_text_datetime == actual_text_datetime

    def test_datapoint_map_created(self):
        """
        Test that a datapoint_map is created after Datapoints are updated.

        Also tests that Datapoint.get_mqtt_topic returns the right thing.
        """
        # Start with an empty string so json.loads below won't fail, which
        # would distract from the actual reason of the test failing.
        self.mqtt_client.userdata = "{}"

        def on_message(client, userdata, msg):
            """
            Store the received message so we can test it's correctness later.
            """
            if msg.topic == "test_connector_4/datapoint_map":
                logger.error(msg.topic)
                logger.error(msg.payload)
                client.userdata = msg.payload
        self.mqtt_client.subscribe("test_connector_4/datapoint_map")
        self.mqtt_client.on_message = on_message

        # Add two datapoints that should occure in the datapoint_map
        test_datapoint_1 = datapoint_factory(
            connector=self.test_connector_4,
            key_in_connector="test_datapoint_map",
            data_format="generic_numeric",
            type="sensor"
        )
        test_datapoint_2 = datapoint_factory(
            connector=self.test_connector_4,
            key_in_connector="test_datapoint_map_2",
            data_format="generic_text",
            type="actuator"
        )
        waited_seconds = 0
        while not self.mqtt_client.userdata:
            time.sleep(0.005)
            waited_seconds += 0.005

            if waited_seconds >= 3:
                raise RuntimeError(
                    'Expected datapoint map not received via MQTT.'
                )

        dp1_topic = "test_connector_4/messages/" + str(test_datapoint_1.id)
        dp2_topic = "test_connector_4/messages/" + str(test_datapoint_2.id)

        # Following the datapoint_map format
        expected_payload = {
            "sensor": {
                test_datapoint_1.key_in_connector: dp1_topic
            },
            "actuator": {
                test_datapoint_2.key_in_connector: dp2_topic
            },
        }

        actual_payload = json.loads(self.mqtt_client.userdata)
        assert actual_payload == expected_payload


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
