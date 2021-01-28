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
    # Don't add a docstring here, the inherited version is fine for documenting
    # the Model.
    #
    ##########################################################################
    #
    # Add special fields that are only required for the API service
    #
    ##########################################################################
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
    example_value = models.CharField(
        max_length=30,
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
        mqtt_topics["schedule"] = topic_base + "schedule"
        mqtt_topics["setpoint"] = topic_base + "setpoint"
        return mqtt_topics


class DatapointValue(DatapointValueTemplate):
    # Don't add a docstring here, the inherited version is fine for documenting
    # the Model.
    #
    # Overload the datapoint to the datapoint defined above.
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the value message belongs to."
        )
    )


class DatapointSchedule(DatapointScheduleTemplate):
    # Don't add a docstring here, the inherited version is fine for documenting
    # the Model.
    #
    # Overload the datapoint to the datapoint defined above.
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the schedule message belongs to."
        )
    )


class DatapointSetpoint(DatapointSetpointTemplate):
    # Don't add a docstring here, the inherited version is fine for documenting
    # the Model.
    #
    # Overload the datapoint to the datapoint defined above.
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the setpoint message belongs to."
        )
    )
