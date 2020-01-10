from datetime import date
from django.db import models
from django.db.models.query import QuerySet
from django.shortcuts import reverse
from django.utils.html import format_html
from django.utils.text import slugify

from admin_interface import connector_mqtt_integration

class Connector(models.Model):
    """
    TODO: Review set and get MQTT topics
    TODO: Ensure that all topics are unique.
    """
    name = models.CharField(
        default='test-connector',
        max_length=50,
        blank=True,
        verbose_name="Connector name"
    )
    mqtt_topic_logs = models.CharField(
        default='/logs',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for logs"
    )
    mqtt_topic_heartbeat = models.CharField(
        default='/heartbeat',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for heartbeat"
    )
    mqtt_topic_available_datapoints = models.CharField(
        default='/available_datapoints',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for available datapoints"
    )
    mqtt_topic_datapoint_map = models.CharField(
        default='/datapoint_map',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for datapoint map"
    )
    mqtt_topic_raw_message_to_db = models.CharField(
        default='/raw_message_to_db',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for raw message to database"
    )
    mqtt_topic_raw_message_reprocess = models.CharField(
        default='/raw_message_reprocess',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for reprocess"
    )
    mqtt_topic_datapoint_message_wildcard = models.CharField(
        default='messages/#',
        max_length=100,
        blank=True,
        verbose_name="MQTT topic for all datapoint messages (wildcard)"
    )
    date_added = models.DateField()

    # def get_mapped_av_datapoints(self):
    #     pass

    # available_datapoints = models.CharField(
    #     choices=[],
    #     blank=True
    # )

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

    # Automatically set MQTT topics to 'connector_name/mqtt_topic'
    def set_mqtt_topics(self):
        connector_attr = self.__dict__
        for attr in connector_attr:
            if attr.startswith("mqtt"):
                if attr.endswith("datapoint_message_wildcard"):
                    connector_attr[attr] = self.name + "/messages/#"
                else:
                    connector_attr[attr] = self.name + "/" + attr[len("mqtt_topic_"):]
        return connector_attr

    def save(self, *args, **kwargs):
        if not self.id:  # New instance
            # Set MQTT topics and set current day as date_added upon saving of connector name of new connector
            self.set_mqtt_topics()
            self.date_added = date.today()

            # TODO: Maybe as post_save signal?
            # Subscribe to the connector topics
            cmi = connector_mqtt_integration.ConnectorMQTTIntegration.get_broker()[0]
            cmi.integrate_new_connector(connector=self, message_types=(self.get_mqtt_topics().keys()))
        super(Connector, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("edit_connector", kwargs={"id": self.id})


class ConnectorLogEntry(models.Model):
    """
    TODO: Why not keeping the log entries when deleting the connector?
    """
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField()
    msg = models.TextField(
        default='',
        verbose_name="Message"
    )
    emitter = models.TextField(
        default='',
    )
    level = models.SmallIntegerField()

    class Meta:
        verbose_name_plural = "Connector log entries"


class ConnectorHeartbeat(models.Model):
    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )
    last_heartbeat = models.DateTimeField()
    next_heartbeat = models.DateTimeField()

    class Meta:
        verbose_name_plural = "Connector heartbeats"


# class ConnectorMessages(models.Model):
#     connector = models.ForeignKey(
#         Connector,
#         on_delete=models.CASCADE
#     )

# class MapperQuerySet(QuerySet):
#     def update(self, **kwargs):
#         print("being updated")
#         super().update(**kwargs)


class ConnectorDatapointTopicMapper(models.Model):
    #objects = MapperQuerySet.as_manager()

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )
    datapoint_type = models.CharField(max_length=8)
    datapoint_key_in_connector = models.TextField(default='')
    mqtt_topic = models.TextField(default='')
    subscribed = models.BooleanField(
        default=False,
        verbose_name="subscribe/ unsubscribe"
    )

    def get_mapping(self):
        conn_id = self.connector.id
        mappers = ConnectorDatapointTopicMapper.objects.filter(connector=conn_id)
        key_topic_mappings = {}
        for mapper in mappers:
            av_dp = ConnectorAvailableDatapoints.objects.filter(connector=conn_id, datapoint_key_in_connector=mapper.datapoint_key_in_connector)[0]
            key_topic_mappings[av_dp.datapoint_key_in_connector] = mapper.mqtt_topic
        return key_topic_mappings

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Connector datapoint to MQTT topic mapping"
        verbose_name_plural = "Connector datapoint to MQTT topic mapping"


class ConnectorAvailableDatapoints(models.Model):
    """
    TODO: Actually subscribe to topics
    TODO: Set subscription status of corresponding available datapoint accordingly -> maybe in conn. mqtt integration (see TODO there)?
    """
    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )

    datapoint_type = models.CharField(max_length=8)
    datapoint_key_in_connector = models.TextField(default='')
    datapoint_example_value = models.TextField(default='')
    subscribed = models.BooleanField(default=False)

    # TODO: Delete the following two lines
    # mapping = ConnectorDatapointTopicMapper.objects.filter(connector=connector, datapoint_key_in_connector=datapoint_key_in_connector)
    # subscribed = getattr(mapping, 'subscribed')  #

    def __str__(self):
        return slugify(self.datapoint_key_in_connector)

    class Meta:
        verbose_name_plural = "Connector available datapoints"


class DeviceMakerManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class DeviceMaker(models.Model):
    friendly_name = models.TextField(
        default='',
        help_text="Human readable device manufacturer or service provider. "
                  "E.g. Aquametro",
        max_length=30
    )
    slug = models.SlugField(
        default='',
        max_length=40
    )
    manager = DeviceMakerManager()

    def __str__(self):
        return self.slug

    def natural_key(self):
        return self.slug


class DeviceType(models.Model):
    friendly_name = models.TextField(
        default='',
        help_text="Human readable device description. "
                  "E.g. room thermostat or heat meter",
        max_length=30

    )
    slug = models.SlugField(
        default='',
        max_length=40
    )


class DeviceVersion(models.Model):
    version = models.TextField(
        default='',
        help_text="Version/model of device, e.g. 2.1",
        max_length=30
    )
    slug = models.SlugField(
        default='',
        max_length=40
    )

    def __str__(self):
        return self.slug


class DeviceLocationFriendlyName(models.Model):
    friendly_name = models.TextField(
        default='',
        help_text="Human readable device location. "
                  "E.g. 3.1.12 or heating cellar"
    )


# class DeviceManager(models.Manager):
#     def get_by_natural_key(self, slug):
#         return self.get(slug=slug)


# class Device(models.Model):
#     """
#     TODO: Uncomment attributes below
#     TODO: How about dynamic meta data?
#     TODO: Fix on_delete to set a meaningful default value.
#     """
#     connector = models.ForeignKey(
#         Connector,
#         on_delete=models.CASCADE
#     )
#     # device_type_friendly_name = models.ForeignKey(
#     #     DeviceType,
#     #     on_delete=models.SET(''),
#     #     name='Device_type'
#     # )
#     # device_location_friendly_name = models.ForeignKey(
#     #     DeviceLocationFriendlyName,
#     #     on_delete=models.SET(''),
#     #     name='Device_location'
#     # )
#     device_name = models.TextField(
#         default='',
#         max_length=30,
#         help_text="Name of device, e.g. Dachs"
#     )
#     # device_maker = models.ForeignKey(
#     #     DeviceMaker,
#     #     on_delete=models.SET(''),
#     #     default=''
#     # )
#     # device_version = models.ForeignKey(
#     #     DeviceVersion,
#     #     on_delete=models.SET(''),
#     #     blank=True,
#     #     default=''
#     #     #limit_choices_to=....
#     # )
#     # device_slug = models.SlugField(
#     #     max_length=150,
#     #     default="{}_{}_{}".format(device_maker, device_name, device_version),
#     # )
#     # is_virtual = models.BooleanField(
#     #     help_text="True for virtual devices like e.g. a webservice."
#     # )
#     # x = models.FloatField(
#     #     null=True,
#     #     default=None,
#     #     help_text="X Position in 3D Model"
#     # )
#     # y = models.FloatField(
#     #     null=True,
#     #     default=None,
#     #     help_text="Y Position in 3D Model"
#     # )
#     # z = models.FloatField(
#     #     null=True,
#     #     default=None,
#     #     help_text="Z Position in 3D Model"
#     # )
#     manager = DeviceManager()
#     #datapoint = models.ManyToManyField(Datapoint, blank=False)
#
#     def __str__(self):
#         return self.device_name #device_type_friendly_name
#
#     # def natural_key(self):
#     #     return self.device_slug


class GenericDevice(models.Model):
    """
    TODO: Write default for regex
    """
    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )

    type = models.TextField(
        default='',
        max_length=30,
        help_text="Descriptive name of this device."
    )

    datapoint_keys_regex = models.TextField(
        default='',
        blank=True,
        help_text="Regular expression to automatically match available datapoints to this device based on their key."
    )

    def __str__(self):
        return self.type

    class Meta:
        abstract = True


class Device(GenericDevice):
    pass


class NonDevice(GenericDevice):
    url = models.URLField(
        blank=True
    )
    pass


class DatapointUnit(models.Model):

    def __str__(self):
        return self.unit_quantity + " [" + self.unit_symbol + "]"

    unit_quantity = models.TextField(
        help_text="The quantity of the unit, e.g. Temperature or Power"
    )
    unit_symbol = models.TextField(
        help_text="The short symbol of the unit, e.g. °C or kW"
    )


class Datapoint(models.Model):
    """
    TODO: Flag if already integrated or new (e.g. because of having installed a new device)
    TODO: How about dynamic meta data?
    TODO: Fix on_delete to set a meaningful default value.
    """

    def html_element_id(self):
        """
        Return the id of the datapoint element.
        """
        return "datapoint_" + str(self.pk)

    def html_element(self):
        """
        Generates the html element to display the value of the datapoint with
        the primary key as id and the default_value field as initial value.
        E.g:
            <div id=datapoint_21>--.-</div>
        """
        element = format_html(
            "<div id={}>{}</div>",
            self.html_element_id(),
            self.default_value,
        )
        return element

    # TODO: uncomment again
    # device = models.ForeignKey(
    #     Device,
    #     on_delete=models.CASCADE
    # )
    # TODO: uncomment again
    # unit = models.ForeignKey(
    #     DatapointUnit,
    #     on_delete=models.SET('')
    # )
    mqtt_topic = models.TextField(
        null=True,
        blank=True,
        editable=False,
        help_text=(
            "The MQTT topic on which the values of this datapoint "
            "are published. Is auto generated for consistency."
        )
    )
    # TODO: remove blank
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
    # TODO: remove blank
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
    # # TODO: remove blank anc change default again
    # default_value = models.FloatField(
    #     default=None,
    #     blank=True,
    #     help_text=(
    #         "The value that is displayed before the latest datapoint values "
    #         "have been received via MQTT."
    #     )
    # )
    datapoint_key_in_connector = models.TextField(default='')


class GenericDatapoint(models.Model):
    """
    TODO: Active/subscribed (or similar) boolean?
    TODO: Abstract model
    """

    def html_element_id(self):
        """
        Return the id of the datapoint element.
        """
        return "datapoint_" + str(self.pk)

    def html_element(self):
        """
        Generates the html element to display the value of the datapoint with
        the primary key as id and the default_value field as initial value.
        E.g:
            <div id=datapoint_21>--.-</div>
        """
        element = format_html(
            "<div id={}>{}</div>",
            self.html_element_id(),
            self.default_value,
        )
        return element

    # TODO: uncomment again
    # device = models.ForeignKey(
    #     Device,
    #     on_delete=models.CASCADE
    # )
    mqtt_topic = models.TextField(
        null=True,
        blank=True,
        editable=False,
        help_text=(
            "The MQTT topic on which the values of this datapoint "
            "are published. Is auto generated for consistency."
        )
    )
    datapoint_key_in_connector = models.TextField(default='')

    last_value = models.TextField(
        default='',
        blank=True,
        help_text=(
            "The last value django is aware of. This is used as an initial "
            "value in pages before updating from MQTT."
            )
        )
    last_timestamp = models.BigIntegerField(
        default=None,
        null=True,
        help_text=(
            "The last timestamp corresponding to last_value above. This is "
            "used as an initial value in pages before updating from MQTT."
        )
    )
    descriptor = models.TextField(default='')

    class Meta:
        abstract = True


class TextDatapoint(GenericDatapoint):
    pass
    # TODO: uncomment again
    # device = models.ForeignKey(
    #     Device,
    #     on_delete=models.CASCADE
    # )


class NumericDatapoint(GenericDatapoint):
    # TODO: uncomment again
    # unit = models.ForeignKey(
    #     DatapointUnit,
    #     on_delete=models.SET('')
    # )
    # TODO: remove blank if not optional
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
    # TODO: remove blank if not optional
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
