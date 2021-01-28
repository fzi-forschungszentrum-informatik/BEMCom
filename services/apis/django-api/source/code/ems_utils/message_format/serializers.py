import json
from datetime import datetime

from rest_framework import serializers

from ems_utils.timestamp import datetime_from_timestamp, timestamp_utc_now

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
                allowed_values = json.loads(datapoint.allowed_values)
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


class DatapointSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer matching the fields of the Datapoint model generated from
    models.DatapointTemplate.
    """

    class Meta:
        fields = [
            "id",
            "origin_id",
            "type",
            "data_format",
            "short_name",
            "description",
            "origin_description",
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

    def __init__(self, DatapointModel):
        """
        Parameters
        ----------
        DatapointModel : Django model
            The datapoint model that is used to identify the nessary fields
            of this serializer.
        """
        self.Meta.model = DatapointModel


class DatapointValueSerializer(serializers.Serializer):
    """
    Value message for a datapoint.

    The value measured by sensor datapoint, or the set value send to an
    actuator.

    TODO: Add help_text.
    """
    value = serializers.CharField(
        allow_null=True
    )
    timestamp = serializers.IntegerField(
        allow_null=False
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

    TODO: Add help_text.
    """
    from_timestamp = serializers.IntegerField(
        allow_null=True,
        help_text=(
            "The time in milliseconds since 1970-01-01 UTC that the value "
            "should be applied. Can be `null` in which case the value should "
            "be applied immediately after the schedule is received."
        )
    )
    to_timestamp = serializers.IntegerField(
        allow_null=True
    )
    value = serializers.CharField(
        allow_null=True
    )

class DatapointScheduleSerializer(serializers.Serializer):
    """
    The schedule is list of actuator values computed by an optimization
    algorithm that should be executed on the specified actuator datapoint
    if the setpoint is not violated.

    TODO: Add help_text.
    """
    schedule = DatapointScheduleItemSerializer(
        many=True,
        read_only=False,
        allow_null=True,
    )
    timestamp = serializers.IntegerField(
        allow_null=False
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
    The user requested value for a one time interval.

    TODO: Add help_text.
    """
    from_timestamp = serializers.IntegerField(
        allow_null=True,
    )
    to_timestamp = serializers.IntegerField(
        allow_null=True,
    )
    preferred_value = serializers.CharField(
        allow_null=True,
    )
    acceptable_values = serializers.ListField(
        child=serializers.CharField(
            allow_null=True
        ),
        allow_null=True,
        required=False,
    )
    min_value = serializers.FloatField(
        allow_null=True,
        required=False,
    )
    max_value = serializers.FloatField(
        allow_null=True,
        required=False,
    )


class DatapointSetpointSerializer(serializers.Serializer):
    """
    Represents the demand that a user specifies for a datapoint, i.e. the
    range of values (or single value) the user is willing to except.

    TODO: Add help_text.
    """
    setpoint = DatapointSetpointItemSerializer(
        many=True,
        read_only=False,
        allow_null=True
    )
    timestamp = serializers.IntegerField(
        allow_null=False
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