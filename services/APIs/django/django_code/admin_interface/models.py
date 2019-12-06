from django.db import models
from django.utils.html import format_html


class Connector(models.Model):
    """
    TODO: Ensure that all topics are unique.
    """
    name = models.TextField(
        default=''
    )
    mqtt_topic_logs = models.TextField(
        default='',
    )
    mqtt_topic_heartbeat = models.TextField(
        default='',
    )
    mqtt_topic_available_datapoints = models.TextField(
        default='',
    )
    mqtt_topic_datapoint_map = models.TextField(
        default='',
    )


class ConnectorLogEntry(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField()
    msg = models.TextField(
        default='',
    )
    emitter = models.TextField(
        default='',
    )
    level = models.SmallIntegerField()


class ConnectorHeartbeat(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    last_heartbeat = models.DateTimeField()
    next_heartbeat = models.DateTimeField()


class ConnectorAvailableDatapoints(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    datapoint_type = models.CharField(max_length=8)
    datapoint_key_in_connector = models.TextField(
        default='',
    )
    datapoint_example_value = models.TextField(
        default='',
    )


class ProviderManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class Provider(models.Model):
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
    manager = ProviderManager()

    def __str__(self):
        return self.friendly_name

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
        return self.version


class DeviceLocationFriendlyName(models.Model):
    friendly_name = models.TextField(
        default='',
        help_text="Human readable device location. "
                  "E.g. 3.1.12 or heating cellar"
    )


class DeviceManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class Device(models.Model):
    """
    TODO: How about dynamic meta data?
    TODO: Fix on_delete to set a meaningful default value.
    """
    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE
    )
    device_type_friendly_name = models.ForeignKey(
        DeviceType,
        on_delete=models.SET(''),
        name='Device_type'
    )
    device_location_friendly_name = models.ForeignKey(
        DeviceLocationFriendlyName,
        on_delete=models.SET(''),
        name='Device_location'
    )
    device_name = models.TextField(
        default='',
        max_length=30,
        help_text="Name of device, e.g. Dachs"
    )
    # device_slug = models.SlugField(
    #     default="{}_{}_{}".format(Provider.slug, device_name, DeviceVersion.slug),
    # )
    is_virtual = models.BooleanField(
        help_text="True for virtual devices like e.g. a webservice."
    )
    x = models.FloatField(
        null=True,
        default=None,
        help_text="X Position in 3D Model"
    )
    y = models.FloatField(
        null=True,
        default=None,
        help_text="Y Position in 3D Model"
    )
    z = models.FloatField(
        null=True,
        default=None,
        help_text="Z Position in 3D Model"
    )
    manager = DeviceManager()
    #datapoint = models.ManyToManyField(Datapoint, blank=False)

    def __str__(self):
        return self.device_type_friendly_name

    # def natural_key(self):
    #     return self.device_slug


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

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE
    )
    unit = models.ForeignKey(
        DatapointUnit,
        on_delete=models.SET('')
    )
    mqtt_topic = models.TextField(
        null=True,
        editable=False,
        help_text=(
            "The MQTT topic on which the values of this datapoint "
            "are published. Is auto generated for consistency."
        )
    )
    min_value = models.FloatField(
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
    max_value = models.FloatField(
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. Is uesed for "
            "automatically scaling plots. Only applicable to datapoints that"
            "carry numeric values."
        )
    )
    default_value = models.FloatField(
        default='--.-',
        blank=True,
        help_text=(
            "The value that is displayed before the latest datapoint values "
            "have been received via MQTT."
        )
    )







