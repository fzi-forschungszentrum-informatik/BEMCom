"""
Fake MQTT Broker and Client for testing the MQTT communication without a live
broker.
"""
import time

class FakeMQTTBroker():
    """
    Handles subscriptions to topics and calls the receive_from_broker methods
    of the fake_clients for each msg on a subscribed topic. Does this
    synchronous one after the other, which is a contrast to real MQTT.
    """

    def __init__(self):
        self.connected_clients = {}
        self.subscribed_topics = {}

    def connect_client(self, client):
        """
        Store the object of each connected client, so we can call
        receive_from_broker of it in publish_on_broker.
        """
        self.connected_clients[id(client)] = client

    def disconnect_client(self, client):
        """
        Remove entry for disconnected client.
        """
        if id(client) in self.connected_clients:
            _ = self.connected_clients.pop(id(client))

    def subscribe_to_topic(self, client, topic):
        """
        Handle a list of clients that have been subscribed for any topic.
        """
        subscribed_clients = self.subscribed_topics.setdefault(topic, [])
        subscribed_clients.append(id(client))
        self.subscribed_topics[topic] = subscribed_clients

    def unsubscribe_from_topic(self, client, topic):
        """
        Handle a list of clients that have been subscribed for any topic.
        """
        subscribed_clients = self.subscribed_topics.setdefault(topic, [])
        if id(client) in subscribed_clients:
            subscribed_clients.remove(id(client))
        # Delete the entry for the topic if no clients are left.
        if not subscribed_clients:
            del self.subscribed_topics[topic]
        else:
            self.subscribed_topics[topic] = subscribed_clients

    def publish_on_broker(self, msg):
        """
        Publish a message will actually call the receive_from_broker for all
        subscribed clients of the msg topic.
        """
        if not isinstance(msg.payload, str):
            raise ValueError(
                'Expected payload as string, got %s instead.' %
                type(msg.payload)
            )

        # Distrubute the message to all subscribed clients.
        subscribed_clients = self.subscribed_topics.setdefault(msg.topic, [])
        for subscribed_client in subscribed_clients:
            # Ignore clients that have been disconnected.
            if subscribed_client not in self.connected_clients:
                continue
            client_object = self.connected_clients[subscribed_client]
            client_object.receive_from_broker(msg)


class FakeMQTTClient():
    """
    A fake client that behaves similar (at least in the relevant parts)
    like paho.mqtt.client.Client, but requires no real broker for testing.
    """
    def __init__(self, fake_broker):
        """
        Init the Client with all setting, especially relevant is setting
        the fake_broker. After calling __init__ the client behaves in many
        points like the object imported with:
        from paho.mqtt.client import Client.
        """
        self._loop_running = False

        self.fake_broker = fake_broker

        # Define callbacks with no action as default.
        self.on_connect = self.do_nothing
        self.on_disconnect = self.do_nothing
        self.on_message = self.do_nothing
        self.on_subscribe = self.do_nothing
        self.on_unsubscribe = self.do_nothing

    def __call__(self, *args, userdata=None, **kwargs):
        """
        Simulates the __init__ of paho.mqtt.client.Client.
        This second call is necessary to ensure that the client instance
        knows about the fake_broker object.
        """
        self.userdata = userdata
        return self

    @staticmethod
    def do_nothing(*args, **kwargs):
        pass

    def connect(self, *args, **kwargs):
        """
        Simulate a successful connection and push semi plausible values to
        the on_connect callback.
        """
        self.fake_broker.connect_client(self)

        client = self
        userdata = self.userdata
        flags = None
        rc = 0
        self.on_connect(client, userdata, flags, rc)

    def disconnect(self, *args, **kwargs):
        """
        Simulate graceful disconnection from broker, i.e. return code 0
        """
        self.fake_broker.disconnect_client(self)

        client = self
        userdata = self.userdata
        rc = 0
        self.on_disconnect(client, userdata, rc)

    def loop_start(self, *args, **kwargs):
        """
        Simulate that the event loop of the client started, hence messages can
        be received if a connection exists.
        """
        self._loop_running = True

    def loop_stop(self, *args, **kwargs):
        """
        Simulate that the event loop of the client stoped, hence no more
        messages are received or sent.
        """
        self._loop_running = False

    def subscribe(self, topic, qos=0):
        """
        Subscribe to topic, can be called as the paho mqtt version.
        See the paho reference for more information.
        """
        topics = []
        if isinstance(topic, str):
            topics.append(topic)
        elif hasattr(topic, '__iter__') and isinstance(topic[0], str):
            topics.append(topic[0])
        elif hasattr(topic, '__iter__'):
            for topic_str, qos in topic:
                topics.append(topic_str)
        for topic_str in topics:
            self.fake_broker.subscribe_to_topic(self, topic_str)

        # TODO: This would only be called once the client is connected.
        # Define plausible values for on_subscribe callback
        client = self
        userdata = self.userdata
        mid = 0
        granted_qos = 0
        self.on_subscribe(client, userdata, mid, granted_qos)

        # The real client returns a (result, mid), where result is a zero
        # on succes and mid is intiger counting up. The values don't
        # matter for our tests.
        return 0, 1

    def unsubscribe(self, topic):
        """
        Unsubscribe from topic, can be called as the paho mqtt version.
        See the paho reference for more information.
        """
        topics = []
        if isinstance(topic, str):
            topics.append(topic)
        elif hasattr(topic, '__iter__'):
            for topic_str in topic:
                topics.append(topic_str)
        for topic_str in topics:
            self.fake_broker.unsubscribe_from_topic(self, topic_str)

        # TODO: This would only be called once the client is connected.
        # Define plausible values for on_subscribe callback
        client = self
        userdata = self.userdata
        mid = 0
        self.on_unsubscribe(client, userdata, mid)

        # The real client returns a (result, mid), where result is a zero
        # on succes and mid is intiger counting up. The values don't
        # matter for our tests.
        return 0, 1

    def publish(self, topic, payload=None, qos=0, retain=False):
        """
        Publish message on fake_broker. Similar to paho.mqtt clients method.
        """
        # Set topic and payload as attributes of object.
        class msg():
            pass
        msg = msg()
        msg.topic = topic
        msg.payload = payload
        self.fake_broker.publish_on_broker(msg)
        # Give async processes some time to process the data.
        # Especially the test_mqtt_integration.py will will fail
        # randomly without this due to concurrent access to 
        # the SQLite DB. 
        time.sleep(0.1)

    def receive_from_broker(self, msg):
        """
        Helper method called by fake_broker. Is responsible for handling the
        incoming message as realistic as possible.
        """
        # Only process messages if the event loop is running, else the
        # paho mqtt client would not call on_message.
        if self._loop_running:
            client = self
            userdata = self.userdata
            message = msg
            self.on_message(client, userdata, message)

    def user_data_set(self, userdata):
        """
        Update the userdata object.
        """
        self.userdata = userdata
