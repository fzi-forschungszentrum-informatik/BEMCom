import json

from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from .connector import Connector


class Datapoint(models.Model):
    """
    Model for a datapoint.

    This model holds the generic information of a datapoint, i.e. the data
    that should be set for every datapoint regardless of which information it
    represents. By default a datapoint can ether hold a numeric information
    (e.g. 2.0912) or a text information (e.g. "OK").

    Depeding on the use case, the datapoint may require (or should be able to
    carry) additional metadata fields. If you encounter Datapoints that require
    other metadata then is defined in DatapointAddition models below, simply
    generate a new DatapointAddition model and extend `data_format_choices`
    and `data_format_addition_models` accordingly.

    TODO: May be replace delete with deactivate, else we will might end with
          entries in the ValueDB with unknown origin (deleted datapoints will
          be rentered but with new id)
    """

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE,
        editable=False,
    )
    is_active = models.BooleanField(
        default=False,
        help_text=(
            "Flag if the connector should publish values for this datapoint."
        )
    )
    # This must be unlimeted to prevent errors from cut away keys while
    # using the datapoint map by the connector.
    key_in_connector = models.TextField(
        editable=False,
        help_text=(
            "Internal key used by the connector to identify the datapoint "
            "in the incoming/outgoing data streams."
        )
    )
    type = models.CharField(
        max_length=8,
        editable=False,
        default=None,
        help_text=(
            "Datapoint type, can be ether sensor or actuator. Is defined by "
            "the connector."
        )
    )
    # Defines the data format of the datapoint, i.e. the additional metadata
    # fields. The 'actual value' (i.e. the first element of the tuple) must
    # match the key in data_format_addition_models.
    #
    # The formats have the following meanings:
    #   numeric: The value of the datapoint can be stored as a float.
    #   text: The value of the datapoint can be stored as a string.
    #   generic: No additional information.
    #   continuous: The value is a continuous variable with an optional max
    #               and min value, that can take any value in between.
    #   discrete: The value of the datapoint can take one value of limited set
    #             of possible values.
    #
    # Be very careful to not change the "generic" string, it's expected
    # exactly like this in a lot of places.
    data_format_choices = [
        ("generic_numeric", "Generic Numeric"),
        ("continuous_numeric", "Continuous Numeric"),
        ("discrete_numeric", "Discrete Numeric"),
        ("generic_text", "Generic Text"),
        ("discrete_text", "Discrete Text"),
    ]
    # Use generic_text as default as it imposes no constraints on the datapoint
    # apart from that the value can be stored as string, which should always
    # be possible as the value has been received as a JSON string.
    data_format = models.CharField(
        max_length=18,
        choices=data_format_choices,
        default="generic_text",
        help_text=(
            "Format of the datapoint value. Additionally defines which meta"
            "data is available for it. See documentation for details."
        )
    )
    example_value = models.CharField(
        max_length=30,
        editable=False,
        help_text=(
            "One example value for this datapoint. Should help admins while "
            "mangeing datapoints, i.e. to specify the correct data format."
        )
    )
    # Don't limit this, people should never need to use abbreviations or
    # shorten their thoughts just b/c the field is too short.
    description = models.TextField(
        editable=True,
        blank=True,
        help_text=(
            "A human readable description of the datapoint targeted on "
            "users of the API wihtout knowledge about connector details."
        )
    )
    #
    ##########################################################################
    #
    # Below all datapoint fields that may or may not be available for a
    # particular datapoint depending on the data_format and type.
    #
    ##########################################################################
    #
    last_value = models.TextField(
        editable=False,
        null=True,
        help_text=(
            "The last value received via MQTT."
        )
    )
    last_value_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )
    last_setpoint = models.TextField(
        editable=False,
        null=True,
        help_text=(
            "The last schedule received via MQTT. "
            "Applicable to actuator datapoints."
        )
    )
    last_setpoint_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
            "Applicable to actuator datapoints."
        )
    )
    last_schedule = models.TextField(
        editable=False,
        null=True,
        help_text=(
            "The last schedule received via MQTT. "
            "Applicable to actuator datapoints."
        )
    )
    last_schedule_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
            "Applicable to actuator datapoints."
        )
    )
    allowed_values = models.TextField(
        blank=False,
        null=False,
        default="[]",
        help_text=(
            "Allowed values. Applicable to discrete valued datapoints. "
            "Must be a valid JSON string."
        )
    )
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. "
            "Applicable to numeric datapoints."
        )
    )
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. "
            "Applicable to numeric datapoints."
        )
    )
    unit = models.TextField(
        editable=True,
        default="",
        blank=True,
        help_text=(
            "The unit in SI notation, e.g.  Mg*m*s^-2 aka. kN. "
            "Applicable to numeric datapoints."
        )
    )

    def __str__(self):
        return slugify(self.key_in_connector)

    def get_mqtt_topic(self):
        """
        Computes the MQTT topic of the datapoint.

        This uses the mqtt_topic_wildcard part of the connector and adds the
        primary key of the Datapoint table. The later alows efficent mapping
        of incoming messages to Datapoint objects.

        Returns:
        --------
        mqtt_topic: str
            A string with the mqtt_topic of the datapoint.
        """
        # Removes the trailing wildcard `#`
        prefix = self.connector.mqtt_topic_datapoint_message_wildcard[:-1]
        return prefix + str(self.id)

    def clean(self):
        """
        """
        try:
            _ = json.loads(self.allowed_values)
        except Exception:
            raise ValidationError(
                "Allowed values contains no valid JSON string."
            )