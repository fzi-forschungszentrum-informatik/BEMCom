from datetime import date

from django.db import models
from django.shortcuts import reverse
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType


class Connector(models.Model):
    """
    The model to store the basic configuration of a connector, that is it's
    name and MQTT topics it communicates over.

    Don't restrict length of name and mqtt fields, this could lead to errors.
    Setting the MQTT topics (and the name hence too) is required for the
    ConnectorMQTTIntegration to work correctly. We hence enforce that these
    fields are not empty and unique.

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
        unique=True,
        verbose_name="MQTT topic for logs"
    )
    mqtt_topic_heartbeat = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for heartbeat"
    )
    mqtt_topic_available_datapoints =models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for available datapoints"
    )
    mqtt_topic_datapoint_map = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for datapoint map"
    )
    mqtt_topic_raw_message_to_db =models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for raw message to database"
    )
    mqtt_topic_raw_message_reprocess = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for reprocess"
    )
    mqtt_topic_datapoint_message_wildcard = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="MQTT topic for all datapoint messages (wildcard)"
    )
    # These two are automatically generated. It makes no sense to edit them
    # my hand.
    added = models.DateTimeField(
        auto_now_add = True,
        editable = False,
    )
    last_changed = models.DateTimeField(
        auto_now = True,
        editable = False,
    )

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    # Get dictionary of the fields defined above with verbose (human-readable) name and connector-specific value
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
        Save the connector, auto populate the MQTT topics on creation.
        """
        if not self.id:  # New instance
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
    by ConnectorMQTTIntegration. They are not intended to be edited manually.
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
    by ConnectorMQTTIntegration. They are not intended to be edited manually.
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


class Datapoint(models.Model):
    """
    Model for a datapoint.

    This model holds the generic information of a datapoint, i.e. the data
    that should be set for every datapoint regardless of which information it
    represents. By default a datapoint can ether hold a numeric information
    (e.g. 2.0912) or a text information (e.g. "OK").

    The use_as attribute of Datapoint defines how the Datapoint should be used.
    It can be ether:
        "not used": The datapoint will not be used, i.e ignored. That means
                    the connector will not publish values for this datapoint
                    over MQTT.
        "numeric":  The datapoint will be used and it represents a numeric
                    information.
        "text":     The datapoint will be used and it represents a string,
                    or at least something that can be stored as a string.

    Depeding on the use case, the datapoint may require (or should be able to
    carry) additional metadata fields. If you encounter Datapoints that require
    other metadata then is defined in NumericDatapointAddition or
    TextDatapointAddition simply generate a new DatapointAddition model and
    extend use_as_choices and `use_as_addition_models` accordingly.
    """

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE,
        editable=False,
    )
    # Defines the usage of the datapoint, i.e. the additional metadata fields.
    # The 'actual value' (i.e. the first element of the tuple) must match the
    # key in use_as_addition_models.
    use_as_choices = [
        ("not used", "Not used"),
        ("numeric", "Numeric"),
        ("text", "Text"),
    ]
    # Mapping to which model to use for the addtional metadata fields.
    # The value must be a dict of valid kwargs expected by
    # django.contrib.contenttypes.models.ContentType.objects.get()
    #
    # Gotcha: The model name must be all lowercase not as in the class name.
    use_as_addition_models = {
        "numeric": {
            "app_label": "admin_interface",
            "model": "numericdatapointaddition",
        },
        "text": {
            "app_label": "admin_interface",
            "model": "textdatapointaddition",
        },
    }
    use_as = models.CharField(
        max_length=8,
        choices=use_as_choices,
        default="not used",
    )
    type = models.CharField(
        max_length=8,
        editable=False,
        default=None,
    )
    # This must be unlimeted to prevent errors from cut away keys while
    # using the datapoint map by the connector.
    key_in_connector = models.TextField(
        editable=False,
    )
    example_value = models.CharField(
        max_length=30,
        editable=False
    )

    def __str__(self):
        return slugify(self.key_in_connector)

    def save(self, *args, **kwargs):
        """
        Handle the potentially changed usage value, and manage (i.e.
        create/delete) the respective objects in the addition models.

        TODO: This is quite complex and might deserve a test or two.
        Relevant test cases would be:
            - The Datapoint is created for the first time and use_as is:
                - not_used
                - numeric and/or text
            - The Datapoint is changed and:
                - No change if use_as is not changed
                - use_as changed:
                    - The old datapoint addition object exists and is deleted.
                    - The old datapoint addition object does not exist and
                      no error is raised.
                    - The new use_as is not_used and no new object is created.
                    - The new use_as is numeric and/or text and a new object is
                      created.
        """

        # New instance, create a new object for the respective
        # Addition. Assume that until now no such object in of the
        # addition models exists.
        if not self.id:
            # At first trigger a save of self, this is required that we can
            # use it as a relation.
            super(Datapoint, self).save(*args, **kwargs)

            # This is False for "not used" and potentially an other
            # datapoint usage pattern that requires no additional metadata.
            try:
                if self.use_as in self.use_as_addition_models:
                    ct_kwargs = self.use_as_addition_models[self.use_as]
                    addition_type = ContentType.objects.get(**ct_kwargs)
                    addition_model = addition_type .model_class()
                    addition_model(
                        datapoint=self,
                    ).save()
            except:
                # Undo save if the creation of the addition object failed to
                # prevent inconsistent states in DB.
                Datapoint.objects.get(id=self.id).delete()
                raise
            return

        #
        # Below here only for Existing datapoint instance.
        #
        # Check if use_as has changed and trigger a normal save if not.
        use_as_as_in_db = Datapoint.objects.get(id=self.id).use_as
        if use_as_as_in_db == self.use_as:
            super(Datapoint, self).save(*args, **kwargs)
            return

        # Now we now that use_as has chaged, delete the object for the old
        # datapoint addition (if the if statement below is true there should
        # exist one and only one entry in the respective model, as it should
        # have been created by the last run of this method)
        if use_as_as_in_db in self.use_as_addition_models:
            ct_kwargs = self.use_as_addition_models[use_as_as_in_db]
            addition_type = ContentType.objects.get(**ct_kwargs)
            addition_model = addition_type.model_class()
            # DatapointAddition should use a OneToOne relation, hence there
            # should be onyl one entry for this query.
            addition_model.objects.get(datapoint=self.id).delete()

        # Finally create the new datapoint addition entry if applicable.
        if self.use_as in self.use_as_addition_models:
            ct_kwargs = self.use_as_addition_models[self.use_as]
            addition_type = ContentType.objects.get(**ct_kwargs)
            addition_model = addition_type.model_class()
            addition_model(
                datapoint=self,
            ).save()

        super(Datapoint, self).save(*args, **kwargs)


class TextDatapointAddition(models.Model):
    """
    This extends the Datapoint model with metadata specific for text
    datapoints.
    """

    # The metadata belongs to exactly one datapoint.
    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        primary_key=True,
        editable=False,
    )
    last_value = models.TextField(
        editable=False,
        null=True,
        help_text=(
            "The last value received via MQTT."
        )
    )
    last_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )


#class DatapointUnit(models.Model):
#
#    def __str__(self):
#        return self.unit_quantity + " [" + self.unit_symbol + "]"
#
#    unit_quantity = models.TextField(
#        help_text="The quantity of the unit, e.g. Temperature or Power"
#    )
#    unit_symbol = models.TextField(
#        help_text="The short symbol of the unit, e.g. °C or kW"
#    )


class NumericDatapointAddition(models.Model):
    """
    This extends the Datapoint model with metadata specific for numeric
    datapoints.
    """

    # The metadata belongs to exactly one datapoint.
    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        primary_key=True,
        editable=False,
    )
    last_value = models.FloatField(
        editable=False,
        null=True,
        help_text=(
            "The last value received via MQTT."
        )
    )
    last_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )
#    unit = models.ForeignKey(
#        DatapointUnit,
#        on_delete=models.SET('')
#    )
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. Is uesed for "
            "automatically scaling plots."
        )
    )
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. Is uesed for "
            "automatically scaling plots."
        )
    )