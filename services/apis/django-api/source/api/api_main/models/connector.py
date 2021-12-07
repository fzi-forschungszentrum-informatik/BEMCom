from django.db import models
from django.shortcuts import reverse


class Connector(models.Model):
    """
    The model to store the basic configuration of a connector, that is it's
    name and MQTT topics it communicates over.

    Don't restrict length of name and mqtt fields, this could lead to errors.
    Setting the MQTT topics (and the name hence too) is required for the
    MQTT Integration to work correctly. We hence enforce that these
    fields are not empty and unique. Furthermore we set all mqtt_topics to be
    non editable as other parts of the API rely on the convention introduced
    here (e.g. the MqttToDb class on the wildcard format).

    TODO: Review set and get MQTT topics
    """

    name = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="Connector name",
    )
    mqtt_topic_logs = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for logs"
    )
    mqtt_topic_heartbeat = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for heartbeat"
    )
    mqtt_topic_available_datapoints =models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for available datapoints"
    )
    mqtt_topic_datapoint_map = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for datapoint map"
    )
    mqtt_topic_raw_message_to_db = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for raw message to database"
    )
    mqtt_topic_raw_message_reprocess = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for reprocess"
    )
    mqtt_topic_datapoint_message_wildcard = models.TextField(
        blank=False,
        default=None,
        editable=False,
        unique=True,
        verbose_name="MQTT topic for all datapoint messages (wildcard)"
    )
    # These two are automatically generated. It makes no sense to edit them
    # my hand.
    added = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    last_changed = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    # Get dictionary of the fields defined above with verbose (human-readable)
    # name and connector-specific value
    def get_fields(self):
        connector_fields = {}
        fields = self._meta.get_fields(include_parents=False)[-len(self.__dict__)+1:]
        for field in fields:
            connector_fields[field.verbose_name] = getattr(self, field.name)
        return connector_fields

    def get_mqtt_topics(self):
        mqtt_topics = {}
        for attr in self.__dict__:
            if attr.startswith("mqtt_topic"):
                mqtt_topics[attr] = attr[len("mqtt_topic_"):]
        return mqtt_topics

    def set_mqtt_topics(self):
        """
        Automatically set MQTT topics to 'connector_name/mqtt_topic'
        """
        connector_attr = self.__dict__
        for attr in connector_attr:
            if attr.startswith("mqtt"):
                if attr.endswith("datapoint_message_wildcard"):
                    connector_attr[attr] = self.name + "/messages/#"
                else:
                    connector_attr[attr] = self.name + "/" + attr[len("mqtt_topic_"):]
        return connector_attr

    def save(self, *args, **kwargs):
        """
        Save the connector, auto populate the MQTT topics on creation and on
        changed names.
        """
        self.set_mqtt_topics()
        super(Connector, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("edit_connector", kwargs={"id": self.id})


class ConnectorLogEntry(models.Model):
    """
    Model to story the log messages sent by the connector.

    See the definition of the log message format for more information
    about the fields.

    The objects for this model are automatically generated (received via MQTT)
    by MqttToDb. They are not intended to be edited manually.
    """

    class Meta:
        verbose_name_plural = "Connector log entries"

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE,
        editable=False,
    )
    timestamp = models.DateTimeField(
        editable=False,
    )
    msg = models.TextField(
        default='',
        verbose_name="Log message",
        editable=False,
    )
    emitter = models.TextField(
        default='',
        editable=False,
    )
    LEVEL_CHOICES = [
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARNING"),
        (40, "ERROR"),
        (50, "CRITICAL"),
    ]
    level = models.SmallIntegerField(
        choices=LEVEL_CHOICES,
        editable=False,
    )


class ConnectorHeartbeat(models.Model):
    """
    Model to store the last heartbeat of the connector. Ignore the history,
    it does not seem very interesting.

    See the definition of the heartbeat message format for more information
    about the fields.

    The objects for this model are automatically generated (received via MQTT)
    by MqttToDb. They are not intended to be edited manually.
    """

    class Meta:
        verbose_name_plural = "Connector heartbeats"

    connector = models.OneToOneField(
        Connector,
        on_delete=models.CASCADE,
        editable=False,
    )
    last_heartbeat = models.DateTimeField(
        editable=False,
    )
    next_heartbeat = models.DateTimeField(
        editable=False,
    )
