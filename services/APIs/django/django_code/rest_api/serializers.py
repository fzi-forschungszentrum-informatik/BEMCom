import json
import logging
from datetime import datetime

from rest_framework import serializers

logger = logging.getLogger(__name__)


class DatapointSerializer(serializers.Serializer):
    """
    Show metadata for one/many datapoints.
    """
    id = serializers.IntegerField()
    type = serializers.CharField()
    data_format = serializers.CharField()
    description = serializers.CharField()
    unit = serializers.CharField()
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()
    allowed_values = serializers.JSONField()
    url = serializers.URLField()
    value_url = serializers.URLField()
    schedule_url = serializers.URLField()
    setpoint_url = serializers.URLField()

    def to_representation(self, instance):
        fields_values = {}
        fields_values["id"] = instance.id
        fields_values["type"] = instance.type
        fields_values["data_format"] = instance.data_format
        fields_values["description"] = instance.description
        if "_numeric" in instance.data_format:
            fields_values["unit"] = instance.unit
        if "discrete_" in instance.data_format:
            allowed_values = instance.allowed_values
            try:
                allowed_values = json.loads(allowed_values)
            except Exception:
                logger.exception(
                    "Failed to parse JSON of allowed_values for datapoint "
                    "id: %s. allowed_values field was: %s"
                    % (instance.id, allowed_values)
                )
                allowed_values = None
            fields_values["allowed_values"] = allowed_values
        if "continuous_numeric" in instance.data_format:
            fields_values["min_value"] = instance.min_value
            fields_values["max_value"] = instance.max_value

        # Compute the URLs of the datapoint related messages. Prefer absolute
        # URLs but fall back to relative if we have no request object to
        # determine the absolute path.
        if "request" in self.context and self.context["request"] is not None:
            build_absolute_uri = self.context["request"].build_absolute_uri
        else:
            def build_absolute_uri(rel_path):
                return rel_path

        fields_values["url"] = build_absolute_uri(
            "/datapoint/%s/" % instance.id
        )
        fields_values["value_url"] = fields_values["url"] + "value/"

        # Only actuators have schedules and setpoints.
        if instance.type == "actuator":
            fields_values["schedule_url"] = fields_values["url"] + "schedule/"
            fields_values["setpoint_url"] = fields_values["url"] + "setpoint/"

        return fields_values


class DatapointValueSerializer(serializers.Serializer):
    """
    Return the latest sensor/actuator msg of the datapoint.
    """
    value = serializers.CharField()
    timestamp = serializers.IntegerField()

    def to_representation(self, instance):
        fields_values = {}
        fields_values["value"] = instance.last_value
        # Return datetime in ms.
        if instance.last_value_timestamp is not None:
            timestamp = datetime.timestamp(instance.last_value_timestamp)
            timestamp_ms = round(timestamp * 1000)
            fields_values["timestamp"] = timestamp_ms
        else:
            fields_values["timestamp"] = None
        return fields_values


class DatapointScheduleSerializer(serializers.Serializer):
    """
    TODO: Fix datapoint model and return appropriate values here.
    """
    schedule = serializers.CharField()
    timestamp = serializers.IntegerField()

    def to_representation(self, instance):
        fields_values = {}
        return fields_values


class DatapointSetpointSerializer(serializers.Serializer):
    """
    TODO: Fix datapoint model and return appropriate values here.
    """
    setpoint = serializers.CharField()
    timestamp = serializers.IntegerField()

    def to_representation(self, instance):
        fields_values = {}
        return fields_values
