"""
Defines models for Datapoint and it's three message types. See the
documentation in ems_utils.message_format for details.
"""
import json
import math

from django.db import models

from .connector import Connector
from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointLastValueTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate
from ems_utils.message_format.models import DatapointLastSetpointTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate
from ems_utils.message_format.models import DatapointLastScheduleTemplate


class Datapoint(DatapointTemplate):
    """
    Similar to the generic Datapoint model (see docstring in DatapointTemplate
    for more information) but with fields adapted to the needs of API service.
    """

    # Overload the docstring with the one of DatapointTemplate for the
    # automatic generation of documentation in schema, as the original
    # docstring contains more general descriptions.
    __doc__ = DatapointTemplate.__doc__.strip()

    class Meta:
        # This should hopefully prevent that datapoints can be inserted
        # multiple times due to race conditions.
        constraints = [
            models.UniqueConstraint(
                fields=["connector", "key_in_connector", "type"],
                name="Datapoint key_in_connector, connector and type unique together",
            )
        ]

    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    is_active = models.BooleanField(
        default=False,
        help_text=(
            "Flag if the connector should publish values for this datapoint."
        ),
    )
    # This must be unlimeted to prevent errors from cut away keys while
    # using the datapoint map by the connector.
    key_in_connector = models.TextField(
        help_text=(
            "Internal key used by the connector to identify the datapoint "
            "in the incoming/outgoing data streams."
        )
    )
    # This exists, but it should not be editable and update help text.
    type = models.CharField(
        max_length=8,
        default=None,
        help_text=(
            "Datapoint type, can be ether sensor or actuator. Is defined by "
            "the connector."
        ),
    )
    example_value = models.JSONField(
        editable=False,
        null=True,
        help_text=(
            "One example value for this datapoint. Should help admins while "
            "mangeing datapoints, i.e. to specify the correct data format."
        ),
    )
    # Delete this field, the API IS THE origin of meta data.
    exclude = ("origin_id",)

    def __str__(self):
        if self.short_name is not None:
            return self.connector.name + "/" + self.short_name
        else:
            return self.connector.name + "/" + self.key_in_connector

    def get_mqtt_topics(self):
        """
        Computes the MQTT topic of the datapoint.

        This uses the mqtt_topic_wildcard part of the connector and adds the
        primary key of the Datapoint table. The later alows efficent mapping
        of incoming messages to Datapoint objects.

        Returns:
        --------
        mqtt_topics: dict
            A dict containing a mqtt_topic for each datapoint_msg_type.
        """
        # Removes the trailing wildcard `#`
        prefix = self.connector.mqtt_topic_datapoint_message_wildcard[:-1]
        topic_base = prefix + str(self.id) + "/"
        mqtt_topics = {}
        mqtt_topics["value"] = topic_base + "value"
        if self.type == "actuator":
            mqtt_topics["schedule"] = topic_base + "schedule"
            mqtt_topics["setpoint"] = topic_base + "setpoint"
        return mqtt_topics

    def save(self, *args, **kwargs):
        """
        Disable the inherited save method from ems_utils.
        This Datapoint definition has no origin_id.
        """
        if self.short_name == "":
            self.short_name = None

        # Handle NaN and Inf/-Inf float values as examples.
        # Python JSON can encode/deocode these values but Postgres
        # cannot store them. Hence trasform to string, which is basically
        # the same thing Python does.
        e = self.example_value
        if e is not None and isinstance(e, float):
            if math.isnan(e) or e == float("inf") or e == float("-inf"):
                self.example_value = json.dumps(self.example_value)

        models.Model.save(self, *args, **kwargs)


class DatapointValue(DatapointValueTemplate):
    """
    Similar to the generic DatapointValue model (see docstring in
    DatapointValueTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    # Overload the docstring with the one of DatapointValueTemplate for
    # the automatic generation of documentation in schema, as the original
    # docstring contains more general descriptions.
    __doc__ = DatapointValueTemplate.__doc__.strip()
    #
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="value_messages",
        help_text=("The datapoint that the value message belongs to."),
    )


class DatapointLastValue(DatapointLastValueTemplate):
    """
    Similar to the generic DatapointLastValue model (see docstring in
    DatapointLastValueTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="last_value_message",
        help_text=("The datapoint that the value message belongs to."),
    )

    def save(self, *args, **kwargs):
        """
        Handle NaN and Inf/-Inf float values as examples.

        Similar to above in `example_value`.

        NOTE: This is only necessary for the last value field as the
        usual value will store this as a float number anyway.
        """

        v = self.value
        if v is not None and isinstance(v, float):
            if math.isnan(v) or v == float("inf") or v == float("-inf"):
                self.value = json.dumps(self.value)

        models.Model.save(self, *args, **kwargs)


class DatapointSchedule(DatapointScheduleTemplate):
    """
    Similar to the generic DatapointSchedule model (see docstring in
    DatapointScheduleTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    # Overload the docstring with the one of DatapointScheduleTemplate for
    # the automatic generation of documentation in schema, as the original
    # docstring contains more general descriptions.
    __doc__ = DatapointScheduleTemplate.__doc__.strip()
    #
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="schedule_messages",
        help_text=("The datapoint that the schedule message belongs to."),
    )


class DatapointLastSchedule(DatapointLastScheduleTemplate):
    """
    Similar to the generic DatapointLastSchedule model (see docstring in
    DatapointLastScheduleTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="last_schedule_message",
        help_text=("The datapoint that the schedule message belongs to."),
    )


class DatapointSetpoint(DatapointSetpointTemplate):
    """
    Similar to the generic DatapointSetpoint model (see docstring in
    DatapointSetpointTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    # Overload the docstring with the one of DatapointSetpointTemplate for
    # the automatic generation of documentation in schema, as the original
    # docstring contains more general descriptions.
    __doc__ = DatapointSetpointTemplate.__doc__.strip()
    #
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="setpoint_messages",
        help_text=("The datapoint that the setpoint message belongs to."),
    )


class DatapointLastSetpoint(DatapointLastSetpointTemplate):
    """
    Similar to the generic DatapointLastSetpoint model (see docstring in
    DatapointLastSetpointTemplate for more information) but with the correct
    Datapoint model linked to it.
    """

    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="last_setpoint_message",
        help_text=("The datapoint that the setpoint message belongs to."),
    )
