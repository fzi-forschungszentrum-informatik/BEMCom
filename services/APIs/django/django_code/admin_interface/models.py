from datetime import date
import uuid
from django.db import models
from django.db.models import Max, IntegerField
from django.db.models.query import QuerySet
from django.shortcuts import reverse
from django.utils.html import format_html
from django.utils.text import slugify

from admin_interface import connector_mqtt_integration


class Connector(models.Model):
    """
    @david: all relevant
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

    def __str__(self):
        return self.name

    # def get_fields(self):
    #     """
    #     Return dictionary of the fields defined above with verbose (human-readable) name and connector-specific value.
    #     Is used in connector_detail.html template
    #     @david: not relevant
    #     """
    #     connector_fields = {}
    #     fields = self._meta.get_fields(include_parents=False)[-len(self.__dict__)+1:]
    #     for field in fields:
    #         connector_fields[field.verbose_name] = getattr(self, field.name)
    #     return connector_fields

    def get_mqtt_topic_fields(self):
        """
        :return: list of fields with MQTT topic
        Used as a shortcut to avoid typing all field names
        """
        mqtt_topics_fields = {}
        for attr in self.__dict__:
            if attr.startswith("mqtt_topic"):
                mqtt_topics_fields[attr] = attr[len("mqtt_topic_"):]
        return mqtt_topics_fields

    # Automatically set MQTT topics to 'connector_name/mqtt_topic'
    def populate_mqtt_topic_fields(self):
        """
        Populates each MQTT topic field with <connector-name>/<mqtt-topic>.
        Function is executed upon saving of a new connector object
        Note: Must be adapted if naming convention for fields or topics changes
        """
        connector_attributes = self.__dict__
        for attr in connector_attributes:
            if attr.startswith("mqtt"):
                if attr.endswith("datapoint_message_wildcard"):
                    connector_attributes[attr] = self.name + "/messages/#"
                else:
                    # Get MQTT topic by stripping of "mqtt_topic_" from the field name defined above
                    connector_attributes[attr] = self.name + "/" + attr[len("mqtt_topic_"):]

    def save(self, *args, **kwargs):
        """
        Overridden to perform the following action before saving a new connector object:
            - Automatically define the connector's MQTT topics according a given naming convention
            - Set date_added to today
            - Subscribe to the defined MQTT topics
        """
        if not self.id:  # New instance
            # Set MQTT topics and set current day as date_added upon saving of connector name of new connector
            self.populate_mqtt_topic_fields()
            self.date_added = date.today()

            # TODO: Maybe as post_save signal?
            # Subscribe to the connector topics
            cmi = connector_mqtt_integration.ConnectorMQTTIntegration.get_broker()[0]
            cmi.integrate_new_connector(connector=self, message_types=(self.get_mqtt_topic_fields().keys()))
        super(Connector, self).save(*args, **kwargs)

    # def get_absolute_url(self):
    #     """
    #     Only needed for non-admin pages
    #     """
    #     return reverse("edit_connector", kwargs={"id": self.id})


class ConnectorLogEntry(models.Model):
    """
    TODO: Why not keeping at least some log entries when deleting the connector?
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


class ConnectorAvailableDatapoints(models.Model):
    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )

    datapoint_type = models.CharField(max_length=8)
    datapoint_key_in_connector = models.TextField(default='')
    datapoint_example_value = models.TextField(default='')
    subscribed = models.BooleanField(default=False)
    format = models.TextField(
        choices=[('unused', 'not used'), ('num', 'numeric'), ('text', 'text')],
        default='unused'
    )

    def __str__(self):
        return slugify(self.datapoint_key_in_connector)

    class Meta:
        verbose_name_plural = "Connector available datapoints"


class DeviceMakerManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


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


class DeviceLocationFriendlyName(models.Model):
    friendly_name = models.TextField(
        default='',
        help_text="Human readable device location. "
                  "E.g. 3.1.12 or heating cellar"
    )


class GenericDeviceManager(models.Manager):
    # FYI: self.model returns class

    @staticmethod
    def all_devices_as_dict():
        """
        :return: all devices from all types with name and class identifier
        """
        all_devices = {}
        devices = Device.objects.all().values('type', 'full_id')
        non_devices = NonDevice.objects.all().values('type', 'full_id')
        for d in devices:
            all_devices[d['full_id']] = d['type']
        for n in non_devices:
            all_devices[n['full_id']] = n['type']

        return all_devices


class GenericDevice(models.Model):
    """
    TODO: Write default for regex
    """
    connector = models.ForeignKey(
        Connector,
        on_delete=models.DO_NOTHING
    )
    spec_id = models.PositiveIntegerField(
        editable=False,
        null=True
    )
    type = models.TextField(
        default='',
        max_length=30,
        help_text="Descriptive name of this device."
    )
    location_detail = models.TextField(
        default='',
        blank=True,
        help_text="Human-readable info about location inside a room, e.g. 'left window'."
    )
    datapoint_keys_regex = models.TextField(
        default='',
        blank=True,
        help_text="Regular expression to automatically match available datapoints to this device based on their key."
    )

    objects = GenericDeviceManager()

    def __str__(self):
        return self.type

    @classmethod
    def get_list_of_subclasses_with_identifier(cls, exclude=None):
        subclasses = {}
        for subclass in cls.__subclasses__():
            subclasses[subclass.get_class_identifier()] = {'class': subclass, 'name': subclass.__name__}
        if exclude is not None:
            for cls_id in exclude:
                del subclasses[cls_id]
        return subclasses

    class Meta:
        abstract = True


class Device(GenericDevice):
    full_id = models.TextField(
        default='',
        editable=False,
        primary_key=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        """
        When a new object is created, set its 'spec_id' to the next increment of the highest existing id.
        The primary key full_id combines the class_identifier 'd' with the spec_id
        """
        if self.spec_id is None:
            max_id = self.__class__.objects.aggregate(max_id=models.Max('spec_id', output_field=models.IntegerField()))['max_id']
            if max_id:
                self.spec_id = max_id + 1
            else:  # max_id is None because this is the first object for this model ever
                self.spec_id = 1
            self.full_id = self.get_class_identifier() + '-' + str(self.spec_id)
        super(self.__class__, self).save(*args, **kwargs)

    @classmethod
    def get_class_identifier(cls):
        return 'd'


class NonDevice(GenericDevice):
    full_id = models.TextField(
        default='',
        editable=False,
        primary_key=True,
        unique=True
    )

    # url = models.URLField(
    #     blank=True
    # )

    def save(self, *args, **kwargs):
        """
        When a new object is created, set its 'spec_id' to the next increment of the highest existing id.
        The primary key full_id ombines the class_identifier 'n' with the spec_id
        """
        if self.spec_id is None:
            max_id = self.__class__.objects.aggregate(max_id=models.Max('spec_id', output_field=models.IntegerField()))['max_id']
            if max_id:
                self.spec_id = max_id + 1
            else:  # max_id is None because this is the first object for this model ever
                self.spec_id = 1
            self.full_id = self.get_class_identifier() + '-' + str(self.spec_id)
        super(self.__class__, self).save(*args, **kwargs)

    @classmethod
    def get_class_identifier(cls):
        return 'n'


class TestDevice(GenericDevice):
    full_id = models.TextField(
        default='',
        editable=False,
        primary_key=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        if self.spec_id is None:
            max_id = self.__class__.objects.aggregate(max_id=models.Max('spec_id', output_field=models.IntegerField()))['max_id']
            if max_id:
                self.spec_id = max_id + 1
            else:  # max_id is None because this is the first object for this model ever
                self.spec_id = 1
            self.full_id = self.get_class_identifier() + '-' + str(self.spec_id)
        super(self.__class__, self).save(*args, **kwargs)

    @classmethod
    def get_class_identifier(cls):
        return 't'


class DatapointUnit(models.Model):

    def __str__(self):
        return self.unit_quantity + " [" + self.unit_symbol + "]"

    unit_quantity = models.TextField(
        help_text="The quantity of the unit, e.g. Temperature or Power"
    )
    unit_symbol = models.TextField(
        help_text="The short symbol of the unit, e.g. °C or kW"
    )


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

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )
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
    descriptor = models.TextField(
        default='',
        blank=True
    )

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
