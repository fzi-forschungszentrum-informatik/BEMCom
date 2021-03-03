"""
Defines models for Datapoint and it's three message types. See the
documentation in ems_utils.message_format for details.
"""
import json

from django.db import models

from .connector import Connector
from ems_utils.message_format.models import DatapointTemplate
from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate

class Datapoint(DatapointTemplate):
    """
    Similar to the generic Datapoint model (see docstring in DatapointTemplate for
    more information) but with fields adapted to the needs of API service.
    """
    # Overload the docstring with the one of DatapointTemplate for the
    # automatic generation of documentation in schema, as the original
    # docstring contains more general descriptions.
    __doc__ = DatapointTemplate.__doc__.strip()
    #
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
    # This exists, but it should not be editable and update help text.
    type = models.CharField(
        max_length=8,
        editable=False,
        default=None,
        help_text=(
            "Datapoint type, can be ether sensor or actuator. Is defined by "
            "the connector."
        )
    )
    example_value = models.TextField(
        editable=False,
        help_text=(
            "One example value for this datapoint. Should help admins while "
            "mangeing datapoints, i.e. to specify the correct data format."
        )
    )
    # Delete these fields, the API IS THE origin of meta data.
    exclude = ("origin_id", "origin_description")

    def __str__(self):
        if self.short_name is not None:
            return (self.connector.name + "/" + self.short_name)
        else:
            return (self.connector.name + "/" + self.key_in_connector)

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
        help_text=(
            "The datapoint that the value message belongs to."
        )
    )

    def save(self, *args, **kwargs):
        """
        Disable the inherited save method from ems_utils.
        We update the last_* fields of Datapoint directly in
        ConnectorMQTTIntegration for better performance.
        """
        # Check if we can store the value as float, which is probably
        # much more storage effiecient, comparing at least one byte
        original_value = self.value
        if self.value is not None:
            try:
                value_float = float(self.value)
                parsable = True
            except ValueError:
                parsable = False

            if parsable:
                self.value_float = value_float
                # AFAIK, null values can be stored quite effieciently by
                # most databases.
                self.value = None

        models.Model.save(self, *args, **kwargs)

        # Restore the original value, for any code that continous to work with
        # the object, but keep the float value. It might become handy.
        self.value = original_value

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if instance.value_float is not None:
            instance.value = str(instance.value_float)
        return instance


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
        help_text=(
            "The datapoint that the schedule message belongs to."
        )
    )

    def save(self, *args, **kwargs):
        """
        Disable the inherited save method from ems_utils.
        We update the last_* fields of Datapoint directly in
        ConnectorMQTTIntegration for better performance.
        """
        models.Model.save(self, *args, **kwargs)


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
        help_text=(
            "The datapoint that the setpoint message belongs to."
        )
    )

    def save(self, *args, **kwargs):
        """
        Disable the inherited save method from ems_utils.
        We update the last_* fields of Datapoint directly in
        ConnectorMQTTIntegration for better performance.
        """
        models.Model.save(self, *args, **kwargs)
