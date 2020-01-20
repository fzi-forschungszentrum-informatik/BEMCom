import pytest

from admin_interface.tests.fake_mqtt import FakeMQTTBroker, FakeMQTTClient
from admin_interface.tests.helpers import TestClassWithFixtures


class TestFakeMQTTClient(TestClassWithFixtures):

    fixture_names = ['capsys']

    def test_on_connect_is_called(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        # set the on connect callback.
        def on_connect(client, userdata, flags, rc):
            print('on_connect called')

        fake_client.on_connect = on_connect
        fake_client.connect()

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'on_connect called\n'

    def test_on_connect_contains_userdata(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client(userdata='on connect userdata')

        # set the on connect callback.
        def on_connect(client, userdata, flags, rc):
            print(userdata)

        fake_client.on_connect = on_connect
        fake_client.connect()

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'on connect userdata\n'

    def test_on_subscribe_is_called(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        # set the on subscribe callback.
        def on_subscribe(client, userdata, mid, granted_qos):
            print('on_subscribe called')

        fake_client.on_subscribe = on_subscribe
        fake_client.subscribe('my/topic')

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'on_subscribe called\n'

    def test_on_subscribe_contains_userdata(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client(userdata='on subscribe userdata')

        # set the on subscribe callback.
        def on_subscribe(client, userdata, mid, granted_qos):
            print(userdata)

        fake_client.on_subscribe = on_subscribe
        fake_client.subscribe('my/topic')

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'on subscribe userdata\n'

    def test_subscribe_can_be_called_paho_style(self):
        """
        I.e. subscribe can be called in three ways. These are:
            subscribe("my/topic", 2)
            subscribe(("my/topic", 1))
            subscribe([("my/topic", 0), ("my/topic2", 2)])
        """
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        # Test that the fake broker received the subscription
        fake_client.subscribe("my/topic", 2)
        assert fake_broker.subscribed_topics["my/topic"] == [id(fake_client)]
        # Reset the dict, for next test.
        fake_broker.subscribed_topics = {}

        fake_client.subscribe(("my/topic", 1))
        assert fake_broker.subscribed_topics["my/topic"] == [id(fake_client)]
        fake_broker.subscribed_topics = {}

        fake_client.subscribe([("my/topic", 0), ("my/topic2", 2)])
        assert fake_broker.subscribed_topics["my/topic"] == [id(fake_client)]
        assert fake_broker.subscribed_topics["my/topic2"] == [id(fake_client)]

    def test_on_message_is_called(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def on_message(client, userdata, message):
            print(
                'on_message called for topic %s with message %s' %
                (message.topic, message.payload)
            )

        fake_client.on_message = on_message

        # Start client operation as we would do for paho.mqtt.client.
        fake_client.connect()
        fake_client.loop_start()

        # Send test message and ensure it will also be received.
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test')

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        expected = 'on_message called for topic my/topic with message test\n'
        assert out == expected

    def test_on_message_contains_userdata(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client(userdata='on message userdata')

        # set the on connect callback.
        def on_message(client, userdata, message):
            print(userdata)

        fake_client.on_message = on_message

        # Start client operation as we would do for paho.mqtt.client.
        fake_client.connect()
        fake_client.loop_start()

        # Send test message and ensure it will also be received.
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test')

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'on message userdata\n'

    def test_publish_on_broker_is_called(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client(userdata='on message userdata')

        # set the on connect callback.
        def publish_on_broker(msg):
            print(msg.payload)

        fake_broker.publish_on_broker = publish_on_broker

        # Start client operation as we would do for paho.mqtt.client.
        fake_client.connect()
        fake_client.loop_start()

        # Send test message and ensure it will also be received.
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test publish on broker')

        # Validate the function has been called.
        out, err = self.capsys.readouterr()
        expected = 'test publish on broker\n'
        assert out == expected


class TestFakeMQTTBroker(TestClassWithFixtures):

    fixture_names = ['capsys']

    def test_receive_from_broker_is_called(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def receive_from_broker(msg):
            print(msg.payload)

        fake_client.receive_from_broker = receive_from_broker

        fake_client.connect()
        fake_client.loop_start()
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test receive from broker')

        out, err = self.capsys.readouterr()
        expected = 'test receive from broker\n'
        assert out == expected

    def test_connect_client(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        fake_client.connect()

        assert id(fake_client) in fake_broker.connected_clients

    def test_subscribe_to_topic(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        fake_client.connect()
        fake_client.subscribe('my/topic')

        assert fake_broker.subscribed_topics['my/topic'] == [id(fake_client)]


class TestFakeMQTTEndToEnd(TestClassWithFixtures):
    """
    Validate that fake_client and fake_broker work well together.
    Also validate that the client will only receive messages if it is connected
    and the event loop is running, as this is a common error scenario, and the
    tests should have a chance of finding these errors.

    TODO: Is this also true for sending messages?
    """

    fixture_names = ['capsys']

    def test_two_clients_receive_msg(self):
        # Setup broker and clients as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client_1 = FakeMQTTClient(fake_broker=fake_broker)
        fake_client_1 = fake_client_1()
        fake_client_2 = FakeMQTTClient(fake_broker=fake_broker)
        fake_client_2 = fake_client_2()

        # Define on_message callback and make clients ready for sending
        # and receiving data.
        def on_message_client_1(client, userdata, message):
            print('client_1 message %s' % message.payload)

        def on_message_client_2(client, userdata, message):
            print('client_2 message %s' % message.payload)

        fake_client_1.connect()
        fake_client_1.loop_start()
        fake_client_1.on_message = on_message_client_1
        fake_client_1.subscribe('my/topic')

        fake_client_2.connect()
        fake_client_2.loop_start()
        fake_client_2.on_message = on_message_client_2
        fake_client_2.subscribe('my/topic')

        fake_client_1.publish('my/topic', 'rocks')

        # Validate that the callbacks have been called.
        out, err = self.capsys.readouterr()
        assert 'client_1 message rocks\n' in out
        assert 'client_2 message rocks\n' in out

    def test_client_receives_from_subsribed_topic_only(self):
        # Setup broker and clients as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        # Define on_message callback and make clients ready for sending
        # and receiving data.
        def on_message_client(client, userdata, message):
            print('Topic: %s' % message.topic)

        fake_client.connect()
        fake_client.loop_start()
        fake_client.on_message = on_message_client
        fake_client.subscribe('my/topic')

        # This msg should be received
        fake_client.publish('my/topic', 'rocks')
        # This one not.
        fake_client.publish('myother/topic', 'sucks')

        # Validate that only the correct message has been received.
        out, err = self.capsys.readouterr()
        assert out == 'Topic: my/topic\n'

    def test_no_message_received_before_connect(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def on_message(client, userdata, message):
            print('Received message')

        fake_client.on_message = on_message

        # Usual Send/receive msg but without calling connect.
        fake_client.loop_start()
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test')

        # Validate the message has not been received.
        out, err = self.capsys.readouterr()
        assert out == ''

    def test_no_message_received_after_disconnect(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def on_message(client, userdata, message):
            print('Received message')

        fake_client.on_message = on_message

        # Usual Send/receive msg but after calling disconnect.
        fake_client.connect()
        fake_client.loop_start()
        fake_client.subscribe('my/topic')
        fake_client.disconnect()
        fake_client.publish('my/topic', 'test')

        # Validate the message has not been received.
        out, err = self.capsys.readouterr()
        assert out == ''

    def test_no_message_received_before_loop_start(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def on_message(client, userdata, message):
            print('Received message')

        fake_client.on_message = on_message

        # Usual Send/receive msg but without calling loop_start.
        fake_client.connect()
        fake_client.subscribe('my/topic')
        fake_client.publish('my/topic', 'test')

        # Validate the message has not been received.
        out, err = self.capsys.readouterr()
        assert out == ''

    def test_no_message_received_after_loop_stop(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client()

        def on_message(client, userdata, message):
            print('Received message')

        fake_client.on_message = on_message

        # Usual Send/receive msg but after calling loop_stop.
        fake_client.connect()
        fake_client.loop_start()
        fake_client.subscribe('my/topic')
        fake_client.loop_stop()
        fake_client.publish('my/topic', 'test')

        # Validate the message has not been received.
        out, err = self.capsys.readouterr()
        assert out == ''
        
    def test_user_data_set_updates_userdata(self):
        # Setup broker and client as one would do in test.
        fake_broker = FakeMQTTBroker()
        fake_client = FakeMQTTClient(fake_broker=fake_broker)
        fake_client = fake_client(userdata='first userdata')

        fake_client.user_data_set(userdata='Second userdata')

        # set the on connect callback.
        def on_connect(client, userdata, flags, rc):
            print(userdata)

        fake_client.on_connect = on_connect
        fake_client.connect()

        # Validate that the callback has been called.
        out, err = self.capsys.readouterr()
        assert out == 'Second userdata\n'


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
