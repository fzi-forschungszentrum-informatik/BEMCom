import json
from datetime import datetime

from rest_framework import serializers

from ems_utils.message_format.models import DatapointValueTemplate
from ems_utils.message_format.models import DatapointSetpointTemplate
from ems_utils.message_format.models import DatapointScheduleTemplate
from ems_utils.timestamp import datetime_from_timestamp, timestamp_utc_now


try:
    # Define a Integer field that is also of format int64 in OpenAPI schema.
    from drf_spectacular.types import OpenApiTypes
    from drf_spectacular.utils import extend_schema_field
    
    @extend_schema_field(OpenApiTypes.INT64)
    class Int64Field(serializers.IntegerField):
        pass
except ModuleNotFoundError:
    # Fallback to normal int field if drf_spectacular is not installed.
    class Int64Field(serializers.IntegerField):
        pass
     

class GenericValidators():
    """
    Generic functions to validate the fields during deserialization.

    Generic Docstring for all validate_* functions

    Arguments:
    ----------
    datapoint: datapoint instance.
        .. matching thecurrently processed message.
    value:
        The value to validate. See also:
        https://www.django-rest-framework.org/api-guide/serializers/#validation

    Returns:
    --------
    value:
        The input value if and only if valid.

    Raises:
    -------
    serializers.ValidationError:
        If input value is not valid.
    """

    @staticmethod
    def validate_value(datapoint, value):

        if "_numeric" in datapoint.data_format:
            # None is also a valid value for a Django float field, also for
            # BEMCom values.
            if value is not None:
                try:
                    value = float(value)
                except ValueError:
                    raise serializers.ValidationError(
                        "Value (%s) for numeric datapoint cannot be parsed to"
                        " float." % value
                    )

        if "continuous_numeric" in datapoint.data_format:
            if datapoint.min_value is not None and value is not None:
                if value < datapoint.min_value:
                    raise serializers.ValidationError(
                        "Value (%s) for numeric datapoint is smaller then "
                        "minimum allowed value (%s)." %
                        (value, datapoint.min_value)
                    )
            if datapoint.max_value is not None and value is not None:
                if value > datapoint.max_value:
                    raise serializers.ValidationError(
                        "Value (%s) for numeric datapoint is larger then "
                        "maximum allowed value (%s)." %
                        (value, datapoint.max_value)
                    )
        if "discrete_" in datapoint.data_format:
            # Could be None or emptry string, both should be handled no values
            # allowed.
            if datapoint.allowed_values:
                allowed_values = datapoint.allowed_values
            else:
                allowed_values = []
            if value not in allowed_values:
                raise serializers.ValidationError(
                    "Value (%s) for discrete datapoint in list of "
                    "allowed_values (%s)." %
                    (value, datapoint.allowed_values)
                )

        return value

    @staticmethod
    def validate_timestamp(datapoint, timestamp):
        # No further checking for None, it's ok.
        if timestamp is None:
            return None
        # Validate that the timestamp can be parsed as int.
        try:
            timestamp = int(timestamp)
        except Exception:
            raise serializers.ValidationError(
                "Timestamp (%s) could not be parsed to integer." %
                str(timestamp)
            )

        # Check that the timestamp is within a reasonable range for
        # milliseconds. Check that the timestamp is within a range of
        # ~3 years.
        now = timestamp_utc_now()
        if timestamp > now + 1e11:
            raise serializers.ValidationError(
                "Timestamp (%s) seems unreasonably high. Check if it is "
                "in milliseconds and contact your adminstrator if this is the "
                "case." %
                str(timestamp)
            )
        if timestamp < now - 1e11:
            raise serializers.ValidationError(
                "Timestamp (%s) seems unreasonably low. Check if it is "
                "in milliseconds and contact your adminstrator if this is the "
                "case." %
                str(timestamp)
            )

        return timestamp

    def validate_schedule(self, datapoint, schedule):
        # None is ok but pointless to check further.
        if schedule is None:
            return schedule

        if not isinstance(schedule, list):
            raise serializers.ValidationError(
                "Schedule (%s) is not a list of schedule items." %
                json.dumps(schedule)
            )

        for schedule_item in schedule:
            if not isinstance(schedule_item, dict):
                raise serializers.ValidationError(
                    "Schedule Item (%s) is not a Dict." %
                    json.dumps(schedule_item)
                )

            # Verify that only the expected keys are given in schedule item.
            if "from_timestamp" not in schedule_item:
                raise serializers.ValidationError(
                    "Key 'from_timestamp' is missing Schedule Item (%s)." %
                    json.dumps(schedule_item)
                )
            if "to_timestamp" not in schedule_item:
                raise serializers.ValidationError(
                    "Key 'to_timestamp' is missing Schedule Item (%s)." %
                    json.dumps(schedule_item)
                )
            if "value" not in schedule_item:
                raise serializers.ValidationError(
                    "Key 'value' is missing Schedule Item (%s)." %
                    json.dumps(schedule_item)
                )
            if len(schedule_item.keys()) > 3:
                raise serializers.ValidationError(
                    "Found unexpected key in Schedule Item (%s)." %
                    json.dumps(schedule_item)
                )

            # Now that we are sure that the message format itself is correct
            # verify that the values are ok.
            si_value = schedule_item["value"]
            si_from_ts = schedule_item["from_timestamp"]
            si_to_ts = schedule_item["to_timestamp"]
            try:
                si_value = self.validate_value(datapoint, si_value)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of value of Schedule Item (%s) failed. The "
                    "error was: %s" %
                    (json.dumps(schedule_item), str(ve.detail))
                )
            if si_from_ts is not None and si_to_ts is not None:
                if si_from_ts >= si_to_ts:
                    raise serializers.ValidationError(
                        "Validation of timestamps of Schedule Item (%s) "
                        "failed. to_timestamp must be larger then "
                        "from_timestamp" %
                        json.dumps(schedule_item)
                    )
            try:
                si_from_ts = self.validate_timestamp(datapoint, si_from_ts)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of from_timestamp of Schedule Item (%s) "
                    "failed. The error was: %s" %
                    (json.dumps(schedule_item), str(ve.detail))
                )

            try:
                si_to_ts = self.validate_timestamp(datapoint, si_to_ts)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of to_timestamp of Schedule Item (%s) "
                    "failed. The error was: %s" %
                    (json.dumps(schedule_item), str(ve.detail))
                )
        return schedule

    def validate_setpoint(self, datapoint, setpoint):
        # None is ok but pointless to check further.
        if setpoint is None:
            return setpoint

        if not isinstance(setpoint, list):
            raise serializers.ValidationError(
                "Setpoint (%s) is not a list of setpoint items." %
                json.dumps(setpoint)
            )

        for setpoint_item in setpoint:
            if not isinstance(setpoint_item, dict):
                raise serializers.ValidationError(
                    "Setpoint Item (%s) is not a Dict." %
                    json.dumps(setpoint_item)
                )

            # Verify that only the expected keys are given in setpoint item.
            expected_setpoint_item_len = 3
            if "from_timestamp" not in setpoint_item:
                raise serializers.ValidationError(
                    "Key 'from_timestamp' is missing in Setpoint Item (%s)." %
                    json.dumps(setpoint_item)
                )
            if "to_timestamp" not in setpoint_item:
                raise serializers.ValidationError(
                    "Key 'to_timestamp' is missing in Setpoint Item (%s)." %
                    json.dumps(setpoint_item)
                )
            if "preferred_value" not in setpoint_item:
                raise serializers.ValidationError(
                    "Key 'preferred_value' is missing in Setpoint Item (%s)." %
                    json.dumps(setpoint_item)
                )
                expected_setpoint_item_len = 3

            if "discrete_" in datapoint.data_format:
                expected_setpoint_item_len = 4
                if "acceptable_values" not in setpoint_item:
                    raise serializers.ValidationError(
                        "Key 'acceptable_values' is missing in Setpoint Item "
                        "(%s)." % json.dumps(setpoint_item)
                    )

            if "continuous_numeric" in datapoint.data_format:
                expected_setpoint_item_len = 5
                if "min_value" not in setpoint_item:
                    raise serializers.ValidationError(
                        "Key 'min_value' is missing in Setpoint Item "
                        "(%s)." % json.dumps(setpoint_item)
                    )
                if "max_value" not in setpoint_item:
                    raise serializers.ValidationError(
                        "Key 'max_value' is missing in Setpoint Item "
                        "(%s)." % json.dumps(setpoint_item)
                    )

            if len(setpoint_item.keys()) > expected_setpoint_item_len:
                raise serializers.ValidationError(
                    "Found unexpected key in Setpoint Item (%s)." %
                    json.dumps(setpoint_item)
                )

            # Now that we are sure that the message format itself is correct
            # verify that the values are ok. min_value, max_value and
            # acceptable_values are not validated. The user may define them
            # at will, while the optimizer should only select these subsets
            # of values for usage which lay within the allowed ranges.
            # The later will be checked while receiveing schedules.
            si_pre_value = setpoint_item["preferred_value"]
            si_from_ts = setpoint_item["from_timestamp"]
            si_to_ts = setpoint_item["to_timestamp"]
            try:
                si_pre_value = self.validate_value(datapoint, si_pre_value)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of preferred_value of Setpoint Item (%s) "
                    "failed. The error was: %s" %
                    (json.dumps(setpoint_item), str(ve.detail))
                )
            if si_from_ts is not None and si_to_ts is not None:
                if si_from_ts >= si_to_ts:
                    raise serializers.ValidationError(
                        "Validation of timestamps of Setpoint Item (%s) "
                        "failed. to_timestamp must be larger then "
                        "from_timestamp" %
                        json.dumps(setpoint_item)
                    )
            try:
                si_from_ts = self.validate_timestamp(datapoint, si_from_ts)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of from_timestamp of Setpoint Item (%s) "
                    "failed. The error was: %s" %
                    (json.dumps(setpoint_item), str(ve.detail))
                )

            try:
                si_to_ts = self.validate_timestamp(datapoint, si_to_ts)
            except serializers.ValidationError as ve:
                raise serializers.ValidationError(
                    "Validation of to_timestamp of Setpoint Item (%s) "
                    "failed. The error was: %s" %
                    (json.dumps(setpoint_item), str(ve.detail))
                )

        return setpoint


class DatapointSerializer(serializers.ModelSerializer):
    """
    This is not functional but just a template for copy&paste.
    Overload the Meta.model variable below to make it work.
    """

    class Meta:
        model = None
        fields = [
            "id",
            "origin_id",
            "type",
            "data_format",
            "short_name",
            "description",
            "min_value",
            "max_value",
            "allowed_values",
            "unit",
            ]
        read_only_fields = [
            "id",
        ]
        # Disable the unqieness check for datapoint. We just update
        # for simplicity.
        extra_kwargs = {
            'origin_id': {
                'validators': [],
            }
        }


class DatapointValueSerializer(serializers.Serializer):
    """
    Serializer for a value message.

    See the docstring of the DatapointValueTemplate model for details.

    Explicitly reusue the help text defined in the models to expose it
    in the API schema.
    """
    # Deactive docstring being pushed to schema, it's not relevant for
    # an API user.
    __doc__ = None
    #
    value = serializers.CharField(
        allow_null=True,
        help_text=DatapointValueTemplate.value.field.help_text,
    )
    timestamp = Int64Field(
        allow_null=False,
        help_text=DatapointValueTemplate.timestamp.field.help_text,
    )

    def to_representation(self, instance):
        fields_values = {}
        fields_values["value"] = instance.value
        # Return datetime in ms.
        if instance.timestamp is not None:
            timestamp = datetime.timestamp(instance.timestamp)
            timestamp_ms = round(timestamp * 1000)
            fields_values["timestamp"] = timestamp_ms
        else:
            fields_values["timestamp"] = None
        return fields_values

    def validate_value(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_value(datapoint, value)

    def validate_timestamp(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_timestamp(datapoint, value)


class DatapointScheduleItemSerializer(serializers.Serializer):
    """
    Represents the optimized actuator value for one interval in time.
    """
    from_timestamp = Int64Field(
        allow_null=True,
        help_text=(
            "The time in milliseconds since 1970-01-01 UTC that the value "
            "should be applied. Can be `null` in which case the value should "
            "be applied immediately after the schedule is received by "
            "the controller."
        ),
    )
    to_timestamp = Int64Field(
        allow_null=True,
        help_text=(
            "The time in milliseconds since 1970-01-01 UTC that the value "
            "should no longer be applied. Can be `null` in which case the "
            "value should be applied forever, or more realistically, until "
            "a new schedule is received."
        ),
    )
    value = serializers.CharField(
        allow_null=True,
        help_text=(
            "The value that should be sent to the actuator datapoint.\n"
            "The value must be larger or equal min_value (as listed in the "
            "datapoint metadata) if the datapoints data format is "
            "continuous_numeric.\n"
            "The value must be smaller or equal max_value (as listed in the "
            "datapoint metadata) if the datapoints data format is "
            "continuous_numeric.\n"
            "The value must be in the list of acceptable_values (as listed "
            "in the datapoint metadata) if the datapoints data format is "
            "discrete."
        )
    )

class DatapointScheduleSerializer(serializers.Serializer):
    """
    Serializer for a schedule message.

    See the docstring of the DatapointScheduleTemplate model for details.

    Explicitly reusue the help text defined in the models to expose it
    in the API schema.
    """
    # Deactive docstring being pushed to schema, it's not relevant for
    # an API user.
    __doc__ = None
    #
    schedule = DatapointScheduleItemSerializer(
        many=True,
        read_only=False,
        allow_null=False,
        help_text=DatapointScheduleTemplate.schedule.field.help_text,
    )
    timestamp = Int64Field(
        allow_null=False,
        help_text=DatapointScheduleTemplate.timestamp.field.help_text,
    )

    def to_representation(self, instance):
        fields_values = {}
        fields_values["schedule"] = instance.schedule
        # Return datetime in ms.
        if instance.timestamp is not None:
            timestamp = datetime.timestamp(instance.timestamp)
            timestamp_ms = round(timestamp * 1000)
            fields_values["timestamp"] = timestamp_ms
        else:
            fields_values["timestamp"] = None
        return fields_values

    def validate_timestamp(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_timestamp(datapoint, value)

    def validate_schedule(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_schedule(datapoint, value)

class DatapointSetpointItemSerializer(serializers.Serializer):
    """
    Represents the user demand for one interval in time.
    """
    from_timestamp = Int64Field(
        allow_null=True,
        help_text=(
            "The time in milliseconds since 1970-01-01 UTC that the setpoint "
            "itme should be applied. Can be `null` in which case the item "
            "should be applied immediately after the setpoint is received by "
            "the controller."
        ),
    )
    to_timestamp = Int64Field(
        allow_null=True,
        help_text=(
            "The time in milliseconds since 1970-01-01 UTC that the setpoint "
            "item should no longer be applied. Can be `null` in which case the "
            "item should be applied forever, or more realistically, until "
            "a new setpoint is received."
        ),
    )
    preferred_value = serializers.CharField(
        allow_null=True,
        help_text=(
            "Specifies the preferred setpoint of the user. This value should "
            "be send to the actuator datapoint by the controller if either no "
            "schedule is applicable, or the current value of the corresponding "
            "sensor datapoint is out of range of `acceptable_values` (for "
            "discrete datapoints) or not between `min_value` and `max_value` "
            "(for continuous datapoints) as defined in this setpoint item.\n"
            "Furthermore, the value of `preferred_value` must match the "
            "requirements of the actuator datapoint, i.e. it must be in "
            "`acceptable_values` (for discrete datapoints) or between "
            "`min_value` and `max_value` (for continuous datapoints) as "
            "specified in the corresponding fields of the actuator datapoint."
        ),
    )
    acceptable_values = serializers.ListField(
        child=serializers.CharField(
            allow_null=True
        ),
        allow_null=True,
        required=False,
        help_text=(
            "Specifies the flexibility of the user regarding the sensor "
            "datapoint for discrete values. That is, it specifies the actually "
            "realized values the user is willing to accept. Consider e.g. the "
            "scenario where a room with a discrete heating control has "
            "currently 16°C. If the user specified this field with [20, 21, 22]"
            " it means that only these three temperature values are acceptable. "
            "This situation would cause the controller to immediately send the "
            "preferred_value to the actuator datapoint, even if the schedule "
            "would define a value that lays within the acceptable range."
        ),
    )
    min_value = serializers.FloatField(
        allow_null=True,
        required=False,
        help_text=(
            "Similar to `acceptable_values` above but defines the minimum value"
            "the user is willing to accept for continuous datapoints."
        ),
    )
    max_value = serializers.FloatField(
        allow_null=True,
        required=False,
        help_text=(
            "Similar to `acceptable_values` above but defines the maximum value"
            "the user is willing to accept for continuous datapoints."
        ),
    )


class DatapointSetpointSerializer(serializers.Serializer):
    """
    Serializer for a setpoint message.

    See the docstring of the DatapointSetpointTemplate model for details.

    Explicitly reusue the help text defined in the models to expose it
    in the API schema.
    """
    # Deactive docstring being pushed to schema, it's not relevant for
    # an API user.
    __doc__ = None
    setpoint = DatapointSetpointItemSerializer(
        many=True,
        read_only=False,
        allow_null=True,
        help_text=DatapointSetpointTemplate.setpoint.field.help_text,
    )
    timestamp = Int64Field(
        allow_null=False,
        help_text=DatapointSetpointTemplate.timestamp.field.help_text,
    )

    def to_representation(self, instance):
        fields_values = {}
        fields_values["setpoint"] = instance.setpoint
        # Return datetime in ms.
        if instance.timestamp is not None:
            timestamp = datetime.timestamp(instance.timestamp)
            timestamp_ms = round(timestamp * 1000)
            fields_values["timestamp"] = timestamp_ms
        else:
            fields_values["timestamp"] = None
        return fields_values

    def validate_timestamp(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_timestamp(datapoint, value)

    def validate_setpoint(self, value):
        datapoint = self.instance
        gv = GenericValidators()
        return gv.validate_setpoint(datapoint, value)
