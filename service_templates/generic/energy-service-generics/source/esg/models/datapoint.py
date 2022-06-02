#!/usr/bin/env python3
"""
Generic definitions of datapoint related data types (aka. messages)
in pydantic for serialization (e.g. to JSON) and for auto generation
of endpoint schemas.

In particular this defines models for handling the following message types:
- Datapoint Value
- Datapoint Setpoint
- Datapoint Schedule

See also the BEMCom documentation on message types:
https://bemcom.readthedocs.io/en/latest/03_message_format.html
"""

from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Dict
from typing import List
from typing import Union

from pydantic import Field
from pydantic import Json
from pydantic import root_validator

from esg.models.base import _BaseModel


class DatapointType(str, Enum):
    """
    Valid values for Datapoint.type.
    """

    sensor = "Sensor"
    actuator = "Actuator"


class DatapointDataFormat(str, Enum):
    """
    Defines the data format of the datapoint, i.e. which additional metadata
    we can expect.

    The formats have the following meanings:
      numeric: The value of the datapoint can be stored as a float.
      text: The value of the datapoint can be stored as a string.
      generic: No additional information.
      continuous: The value is a continuous variable with an optional max
                  and min value, that can take any value in between.
      discrete: The value of the datapoint can take one value of limited set
                of possible values.
      bool: A bool, i.e. only True or False.
      unknown: Unknown format.
    """

    generic_numeric = "Generic Numeric"
    continuous_numeric = "Continuous Numeric"
    discrete_numeric = "Discrete Numeric"
    generic_text = "Generic Text"
    discrete_text = "Discrete Text"
    bool = "Boolean"
    unknown = "Unknown"


class Datapoint(_BaseModel):
    """
    Devices are abstracted as a set of datapoints.

    A datapoint represents one source of information. Devices will typically
    emit information on more then one datapoints. E.g. climate sensor in a
    room might publish temperature and humidity measurements. Both will be
    treated as individual datapoints as this allows us to abstract away the
    complexity of the devices.

    Each datapoint object contains the metadata necessary to interpret
    the datapoint.
    """

    id: int = Field(
        default=None,
        example=1337,
        nullable=True,
        description=("The ID of the datapoint in the central DB."),
    )
    origin: str = Field(
        default=None,
        example="HoLL BEMCom Instance",
        nullable=True,
        description=(
            "This name is used if the datapoint metadata is (partly) "
            "configured in an external application (e.g. BEMCom) and should "
            "be used in the current service (e.g. the EMP). This effectively "
            "allows the current application to use additional datapoints that "
            "do not exist in the external service, which is handy for "
            "mocking UIs and stuff."
        ),
    )
    origin_id: str = Field(
        default=None,
        example="2",
        nullable=True,
        description=(
            "In combination with `origin`, this field allows matching the "
            "ids of the external application with id maintained by the current "
            "application. Note: this field is a string as not all external "
            "applications might use integers as IDs, e.g. consider MQTT topics."
        ),
    )
    short_name: str = Field(
        default=None,
        example="T_zone_s",
        nullable=True,
        description=("A short name to identify the datapoint."),
    )
    type: DatapointType = Field(
        ...,
        example="sensor",
        nullable=False,
        description=(
            "Datapoints can either be of type `sensor` (readable) or "
            "`actuator` (writeable)."
        ),
    )
    data_format: DatapointDataFormat = Field(
        default=DatapointDataFormat.unknown,
        example="Generic Numeric",
        nullable=False,
        description=(
            "Format of the datapoint value. Additionally defines which meta"
            "data is available for it. See Enum docs for details."
        ),
    )
    description: str = Field(
        default="",
        example="Zone Temperature Second Floor.",
        nullable=False,
        description=(
            "A human readable description of the datapoint targeted on "
            "users of the API wihtout knowledge about hardware details."
        ),
    )
    #
    ##########################################################################
    #
    # Below all metadata fields that may or may not be populated for a
    # particular datapoint depending on the data_format and type.
    #
    ##########################################################################
    #
    allowed_values: List[Json] = Field(
        default=None,
        nullable=True,
        description=(
            "Allowed values. Applicable to discrete valued datapoints only."
        ),
    )
    min_value: float = Field(
        default=None,
        nullable=True,
        description=(
            "The minimal expected value of the datapoint. None means no "
            "constraint. Only applicable to `Continuous Numeric` datapoints."
        ),
    )
    max_value: float = Field(
        default=None,
        nullable=True,
        description=(
            "The maximum expected value of the datapoint. None means no "
            "constraint. Only applicable to `Continuous Numeric` datapoints."
        ),
    )
    unit: str = Field(
        default="",
        nullable=False,
        description=(
            "The unit in SI notation, e.g.  Mg*m*s^-2 aka. kN. "
            "Only applicable to `Numeric` datapoints."
        ),
    )


class DatapointList(_BaseModel):
    """
    A list of one or more dataoints.
    """

    __root__: List[Datapoint] = Field(
        ...,
        nullable=False,
        example=[
            {
                "id": 1,
                "origin": "emp_demo_dp_interface",
                "origin_id": "1",
                "short_name": "Test Datapoint 1",
                "type": "Sensor",
                "data_format": "Continuous Numeric",
                "description": (
                    "Example for continuous datapoint defined by an "
                    "external application."
                ),
                "allowed_values": None,
                "min_value": 19,
                "max_value": 25,
                "unit": "°C",
            },
            {
                "id": 2,
                "origin": None,
                "origin_id": None,
                "short_name": "Test Datapoint 2",
                "type": "Sensor",
                "data_format": "Discrete Numeric",
                "description": (
                    "Example for discrete datapoint defined directly in EMP."
                ),
                "allowed_values": ["21.0", "22.0", "23.0"],
                "min_value": None,
                "max_value": None,
                "unit": "°C",
            },
        ],
    )


class DatapointById(_BaseModel):
    """
    A dict of datapoints by ID for simple access in applications.
    """

    __root__: Dict[str, Datapoint] = Field(
        ...,
        nullable=False,
        example={
            "1": {
                "id": 1,
                "origin": "emp_demo_dp_interface",
                "origin_id": "1",
                "short_name": "Test Datapoint 1",
                "type": "Sensor",
                "data_format": "Continuous Numeric",
                "description": (
                    "Example for continuous datapoint defined by an "
                    "external application."
                ),
                "allowed_values": None,
                "min_value": 19,
                "max_value": 25,
                "unit": "°C",
            },
            "2": {
                "id": 2,
                "origin": None,
                "origin_id": None,
                "short_name": "Test Datapoint 2",
                "type": "Sensor",
                "data_format": "Discrete Numeric",
                "description": (
                    "Example for discrete datapoint defined directly in EMP."
                ),
                "allowed_values": ["21.0", "22.0", "23.0"],
                "min_value": None,
                "max_value": None,
                "unit": "°C",
            },
        },
        description=(
            "Note that dict key (ID) is a string here due to limitations "
            "in OpenAPI. See description of `Datapoint` type for additional "
            "details."
        ),
    )


class _Value(_BaseModel):
    """
    A single value item, here as a separate model to prevent redundancy
    while constructing the more complex types below.
    """

    __root__: Json = Field(
        ...,
        example="22.1",
        nullable=True,
        description=(
            "The value as JSON encoded string. This value can "
            "e.g. be a measured value of a sensor datapoint or "
            "a set value pushed to an actuator datapoint."
        ),
    )


class _Time(_BaseModel):
    """
    Like `_Value` but for the corresponding timestamp.
    """

    __root__: datetime = Field(
        ...,
        example=datetime.now(tz=timezone.utc),
        nullable=False,
        description=(
            "The time corresponding to the value was measured or the "
            "message was created."
        ),
    )


class ValueMessage(_BaseModel):
    """
    Represents one value at one point in time.
    """

    # Note: The example values are taken just fine from `_Value` and `_Time`.
    value: _Value
    time: _Time


class ValueMessageByDatapointId(_BaseModel):
    """
    A single value message for zero or more Datapoints, e.g. to report the
    last values of multiple Datapoints.
    """

    __root__: Dict[str, ValueMessage] = Field(
        ...,
        nullable=False,
        example={
            "1": {"value": "24.2", "time": "2022-04-25T10:32:58.593870+00:00"},
            "2": {"value": "true", "time": "2022-04-25T10:04:39+00:00"},
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class ValueMessageList(_BaseModel):
    """
    Represents a list of Value Messages, e.g. a time series of measured values.
    """

    __root__: List[ValueMessage] = Field(
        ...,
        nullable=False,
        example=[
            {"value": "24.2", "time": "2022-04-25T10:32:58.593870+00:00"},
            {"value": "true", "time": "2022-04-25T10:34:39+00:00"},
            {"value": '"A string"', "time": "2022-04-25T10:37:07+00:00"},
        ],
    )


class ValueMessageListByDatapointId(_BaseModel):
    """
    Contains one or more value messages for one or more datapoints.
    Only preferable over `ValueDataFrame` if time values are not aligned.
    """

    __root__: Dict[str, ValueMessageList] = Field(
        ...,
        nullable=False,
        example={
            "1": [
                {"value": "true", "time": "2022-04-25T10:13:47+00:00"},
                {"value": '"A string"', "time": "2022-04-25T10:27:07+00:00"},
            ],
            "2": [
                {"value": "21.0", "time": "2022-04-25T10:13:06+00:00"},
                {"value": "22.0", "time": "2022-04-25T10:13:19+00:00"},
            ],
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class ValueDataFrameColumn(_BaseModel):
    """
    A list of values, equivalent to one column in pandas DataFrame.
    """

    __root__: List[_Value] = Field(
        ..., nullable=False,
    )


class ValueDataFrame(_BaseModel):
    """
    A pandas DataFrame like representation of datapoint values. The `values`
    field holds a dict with datapoint IDs as keys and lists of values as items.
    The `times` field contains the corresponding time values applicable to
    all datapoint value columns.
    """

    # Note that it is not possible to embed `List[_Value]` directly into
    # `Dict` as this would break `construct_recursive` on this model.
    values: Dict[str, ValueDataFrameColumn] = Field(
        ...,
        example={
            "1": ["22.1", None, "22.3"],
            "2": ['"sequence"', '"of"', '"strings"'],
            "42": ["true", "true", "false"],
        },
        nullable=False,
    )
    times: List[_Time] = Field(
        ...,
        example=[
            "2022-01-03T18:00:00+00:00",
            "2022-01-03T18:15:00+00:00",
            "2022-01-03T18:30:00+00:00",
        ],
        nullable=False,
    )

    @root_validator
    def check_times_and_values_same_size(cls, values):
        """
        """
        len_of_index = len(values.get("times"))
        for column_name in values.get("values"):
            len_of_column = len(values.get("values").get(column_name).__root__)
            error_msg = (
                "Length ({}) of values column '{}' doesn't match length of "
                "times index ({})".format(
                    len_of_column, column_name, len_of_index
                )
            )
            assert len_of_column == len_of_index, error_msg

        return values


class ScheduleItem(_BaseModel):
    """
    Represents the optimized actuator value for one interval in time.
    """

    from_timestamp: Union[datetime, None] = Field(
        ...,
        example=datetime.now(tz=timezone.utc),
        nullable=True,
        description=(
            "The time that `value` should be applied. Can be `null` in "
            "which case `value` should be applied immediately after the "
            "schedule is received by the controller."
        ),
    )
    to_timestamp: Union[datetime, None] = Field(
        ...,
        example=datetime.now(tz=timezone.utc),
        nullable=True,
        description=(
            "The time that `value` should no longer be applied. Can be "
            "`null` in which case `value` should be applied forever, "
            "or more realistically, until a new schedule is received."
        ),
    )
    # TODO: Might want to add a validator that checks if value matches the
    #       constraints defined in the corresponding datapoint. Something
    #       similar has already been implemented in BEMCom. See here:
    #       https://github.com/fzi-forschungszentrum-informatik/BEMCom/blob/927763a5a3c05eceb6bfb0b48e4b47600e2889ff/services/apis/django-api/source/api/ems_utils/message_format/serializers.py#L31
    value: _Value = Field(
        description=(
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
        ),
    )


class Schedule(_BaseModel):
    """
    A schedule, i.e. a list holding zero or more `ScheduleItem`.
    """

    __root__: List[ScheduleItem] = Field(..., nullable=False)


class ScheduleMessage(_BaseModel):
    """
    The schedule is a list of actuator values computed by an optimization
    algorithm that should be executed on the specified actuator datapoint
    as long as the setpoint constraints are not violated.
    """

    schedule: Schedule = Field(
        ..., nullable=False,
    )
    time: _Time


class ScheduleMessageByDatapointId(_BaseModel):
    """
    A single schedule message for zero or more Datapoints, e.g. to report the
    last schedules of multiple Datapoints.
    """

    __root__: Dict[str, ScheduleMessage] = Field(
        ...,
        nullable=False,
        example={
            "1": {
                "schedule": [
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "value": "21.0",
                    }
                ],
                "time": "2022-04-22T01:21:32.000100+00:00",
            },
            "2": {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": "2022-02-22T03:00:00+00:00",
                        "value": "null",
                    },
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "value": '"true"',
                    },
                    {
                        "from_timestamp": "2022-02-22T03:15:00+00:00",
                        "to_timestamp": None,
                        "value": "false",
                    },
                ],
                "time": "2022-04-22T01:21:25+00:00",
            },
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class ScheduleMessageList(_BaseModel):
    """
    Represents a list of schedule messages.
    """

    __root__: List[ScheduleMessage] = Field(
        ...,
        nullable=False,
        example=[
            {
                "schedule": [
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "value": "21.0",
                    }
                ],
                "time": "2022-04-22T01:21:32.000100+00:00",
            },
            {
                "schedule": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": "2022-02-22T03:00:00+00:00",
                        "value": "null",
                    },
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "value": '"true"',
                    },
                    {
                        "from_timestamp": "2022-02-22T03:15:00+00:00",
                        "to_timestamp": None,
                        "value": "false",
                    },
                ],
                "time": "2022-04-22T01:21:25+00:00",
            },
        ],
    )


class ScheduleMessageListByDatapointId(_BaseModel):
    """
    Contains one or more schedule messages for one or more datapoints.
    """

    __root__: Dict[str, ScheduleMessageList] = Field(
        ...,
        nullable=False,
        example={
            "1": [
                {
                    "schedule": [
                        {
                            "from_timestamp": "2022-02-22T03:00:00+00:00",
                            "to_timestamp": "2022-02-22T03:15:00+00:00",
                            "value": "21.0",
                        }
                    ],
                    "time": "2022-04-22T01:21:32.000100+00:00",
                },
                {
                    "schedule": [
                        {
                            "from_timestamp": None,
                            "to_timestamp": "2022-02-22T03:00:00+00:00",
                            "value": "null",
                        },
                        {
                            "from_timestamp": "2022-02-22T03:00:00+00:00",
                            "to_timestamp": "2022-02-22T03:15:00+00:00",
                            "value": '"true"',
                        },
                        {
                            "from_timestamp": "2022-02-22T03:15:00+00:00",
                            "to_timestamp": None,
                            "value": "false",
                        },
                    ],
                    "time": "2022-04-22T01:21:25+00:00",
                },
            ],
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class SetpointItem(_BaseModel):
    """
    Represents the user demand for one interval in time.
    """

    from_timestamp: Union[datetime, None] = Field(
        ...,
        example=datetime.now(tz=timezone.utc),
        nullable=True,
        description=(
            "The time that the setpoint should be applied. Can be `null` in "
            "which case it should be applied immediately after the "
            "setpoint is received by the controller."
        ),
    )
    to_timestamp: Union[datetime, None] = Field(
        ...,
        example=datetime.now(tz=timezone.utc),
        nullable=True,
        description=(
            "The time that the setpoint should no longer be applied. Can be "
            "`null` in which case it should be applied forever, "
            "or more realistically, until a new setpoint is received."
        ),
    )
    # TODO: Might want to add a validator that checks if `preferred_value`,
    #       `acceptable_values`, `min_value` and `max_value` match the
    #       constraints defined in the corresponding datapoint. Something
    #       similar has already been implemented in BEMCom. See here:
    #       https://github.com/fzi-forschungszentrum-informatik/BEMCom/blob/927763a5a3c05eceb6bfb0b48e4b47600e2889ff/services/apis/django-api/source/api/ems_utils/message_format/serializers.py#L31
    preferred_value: _Value = Field(
        ...,
        nullable=True,
        description=(
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
    acceptable_values: List[_Value] = Field(
        default=None,
        nullable=True,
        description=(
            "Specifies the flexibility of the user regarding the sensor "
            "datapoint for discrete values. That is, it specifies the actually "
            "realized values the user is willing to accept. Consider e.g. the "
            "scenario where a room with a discrete heating control has "
            "currently 16°C. If the user specified this field with [20, 21, 22]"
            " it means that only these three temperature values are "
            "acceptable. This situation would cause the controller to "
            "immediately send the preferred_value to the actuator datapoint, "
            "even if the schedule would define a value that lays within the "
            "acceptable range."
        ),
    )
    min_value: float = Field(
        default=None,
        nullable=True,
        description=(
            "Similar to `acceptable_values` but defines the minimum value"
            "the user is willing to accept for continuous datapoints."
        ),
    )
    max_value: float = Field(
        default=None,
        nullable=True,
        description=(
            "Similar to `acceptable_values` but defines the maximum value"
            "the user is willing to accept for continuous datapoints."
        ),
    )


class Setpoint(_BaseModel):
    """
    A setpoint, i.e. a list holding zero or more `SetpointItem`.
    """

    __root__: List[SetpointItem] = Field(..., nullable=False)


class SetpointMessage(_BaseModel):
    """
    The setpoint specifies the demand of the users of the system. The setpoint
    must hold a preferred_value which is the value the user would appreciate
    most, and can additionally define flexibility of values the user would also
    accept. The setpoint message is used by optimization algorithms as
    constraints while computing schedules, as well as by controller services
    to ensure that the demand of the user is always met.
    """

    setpoint: Setpoint = Field(
        ..., nullable=False,
    )
    time: _Time


class SetpointMessageByDatapointId(_BaseModel):
    """
    A single setpoint message for zero or more Datapoints, e.g. to report the
    last setpoints of multiple Datapoints.
    """

    __root__: Dict[str, SetpointMessage] = Field(
        ...,
        nullable=False,
        example={
            "1": {
                "setpoint": [
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "preferred_value": "21.0",
                        "acceptable_values": None,
                        "max_value": 23.2,
                        "min_value": 17.4,
                    }
                ],
                "time": "2022-04-22T01:21:32.000100+00:00",
            },
            "2": {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": "2022-02-22T03:00:00+00:00",
                        "preferred_value": "null",
                        "acceptable_values": None,
                        "max_value": None,
                        "min_value": None,
                    },
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "preferred_value": '"true"',
                        "acceptable_values": ['"true"', '"other string"'],
                        "max_value": None,
                        "min_value": None,
                    },
                    {
                        "from_timestamp": "2022-02-22T03:15:00+00:00",
                        "to_timestamp": None,
                        "preferred_value": "false",
                        "acceptable_values": ["true", "false"],
                        "max_value": None,
                        "min_value": None,
                    },
                ],
                "time": "2022-04-22T01:21:25+00:00",
            },
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class SetpointMessageList(_BaseModel):
    """
    Represents a list of setpoint messages.
    """

    __root__: List[SetpointMessage] = Field(
        ...,
        nullable=False,
        example=[
            {
                "setpoint": [
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "preferred_value": "21.0",
                        "acceptable_values": None,
                        "max_value": 23.2,
                        "min_value": 17.4,
                    }
                ],
                "time": "2022-04-22T01:21:32.000100+00:00",
            },
            {
                "setpoint": [
                    {
                        "from_timestamp": None,
                        "to_timestamp": "2022-02-22T03:00:00+00:00",
                        "preferred_value": "null",
                        "acceptable_values": None,
                        "max_value": None,
                        "min_value": None,
                    },
                    {
                        "from_timestamp": "2022-02-22T03:00:00+00:00",
                        "to_timestamp": "2022-02-22T03:15:00+00:00",
                        "preferred_value": '"true"',
                        "acceptable_values": ['"true"', '"other string"'],
                        "max_value": None,
                        "min_value": None,
                    },
                    {
                        "from_timestamp": "2022-02-22T03:15:00+00:00",
                        "to_timestamp": None,
                        "preferred_value": "false",
                        "acceptable_values": ["true", "false"],
                        "max_value": None,
                        "min_value": None,
                    },
                ],
                "time": "2022-04-22T01:21:25+00:00",
            },
        ],
    )


class SetpointMessageListByDatapointId(_BaseModel):
    """
    Contains one or more setpoint messages for one or more datapoints.
    """

    __root__: Dict[str, SetpointMessageList] = Field(
        ...,
        nullable=False,
        example={
            "1": [
                {
                    "setpoint": [
                        {
                            "from_timestamp": "2022-02-22T03:00:00+00:00",
                            "to_timestamp": "2022-02-22T03:15:00+00:00",
                            "preferred_value": "21.0",
                            "acceptable_values": None,
                            "max_value": 23.2,
                            "min_value": 17.4,
                        }
                    ],
                    "time": "2022-04-22T01:21:32.000100+00:00",
                },
                {
                    "setpoint": [
                        {
                            "from_timestamp": None,
                            "to_timestamp": "2022-02-22T03:00:00+00:00",
                            "preferred_value": "null",
                            "acceptable_values": None,
                            "max_value": None,
                            "min_value": None,
                        },
                        {
                            "from_timestamp": "2022-02-22T03:00:00+00:00",
                            "to_timestamp": "2022-02-22T03:15:00+00:00",
                            "preferred_value": '"true"',
                            "acceptable_values": ['"true"', '"other string"'],
                            "max_value": None,
                            "min_value": None,
                        },
                        {
                            "from_timestamp": "2022-02-22T03:15:00+00:00",
                            "to_timestamp": None,
                            "preferred_value": "false",
                            "acceptable_values": ["true", "false"],
                            "max_value": None,
                            "min_value": None,
                        },
                    ],
                    "time": "2022-04-22T01:21:25+00:00",
                },
            ],
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class ForecastMessage(_BaseModel):
    """
    A forecast for a datapoint value for one point in time.
    """

    mean: float = Field(
        ...,
        example=21.5,
        nullable=False,
        description=("The expected value at `time`."),
    )
    std: float = Field(
        default=None,
        example=1.0,
        nullable=True,
        description=(
            "The standard deviation (uncertainty) of `mean` at `time`. "
            "This assumes that the forecast error is Gaussian distributed."
        ),
    )
    p05: float = Field(
        default=None,
        example=19.85,
        nullable=True,
        description=(
            "The 5% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is larger then this value with a "
            "probability of 95%."
        ),
    )
    p10: float = Field(
        default=None,
        example=20.22,
        nullable=True,
        description=(
            "The 10% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is larger then this value with a "
            "probability of 90%."
        ),
    )
    p25: float = Field(
        default=None,
        example=20.83,
        nullable=True,
        description=(
            "The 25% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is larger then this value with a "
            "probability of 75%."
        ),
    )
    p50: float = Field(
        default=None,
        example=21.5,
        nullable=True,
        description="The 50% percentile of the forecast, i.e. the median.",
    )
    p75: float = Field(
        default=None,
        example=22.17,
        nullable=True,
        description=(
            "The 75% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is smaller then this value with a "
            "probability of 75%."
        ),
    )
    p90: float = Field(
        default=None,
        example=22.78,
        nullable=True,
        description=(
            "The 90% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is smaller then this value with a "
            "probability of 90%."
        ),
    )
    p95: float = Field(
        default=None,
        example=23.15,
        nullable=True,
        description=(
            "The 95% percentile of the forecast, i.e. it is predicted that "
            "finally observed value is smaller then this value with a "
            "probability of 95%."
        ),
    )
    time: _Time


class ForecastMessageList(_BaseModel):
    """
    A list of forecast messages, e.g. a full forecast for a datapoint
    for multiple times in the future.
    """

    __root__: List[ForecastMessage] = Field(
        ...,
        nullable=False,
        example=[
            {
                "mean": 21.0,
                "std": 1.0,
                "p05": 19.35,
                "p10": 19.72,
                "p25": 20.33,
                "p50": 21.0,
                "p75": 21.67,
                "p90": 22.28,
                "p95": 22.65,
                "time": "2022-02-22T02:45:00+00:00",
            },
            {
                "mean": 21.2,
                "std": 1.1,
                "p05": 19.39,
                "p10": 19.79,
                "p25": 20.46,
                "p50": 21.2,
                "p75": 21.94,
                "p90": 22.61,
                "p95": 23.01,
                "time": "2022-02-22T03:45:00+00:00",
            },
        ],
    )


class ForecastMessageListByDatapointId(_BaseModel):
    """
    Contains forecasts for one or more defined datapoints.
    """

    __root__: Dict[str, ForecastMessageList] = Field(
        ...,
        nullable=False,
        example={
            "1": [
                {
                    "mean": 21.0,
                    "std": 1.0,
                    "p05": 19.35,
                    "p10": 19.72,
                    "p25": 20.33,
                    "p50": 21.0,
                    "p75": 21.67,
                    "p90": 22.28,
                    "p95": 22.65,
                    "time": "2022-02-22T02:45:00+00:00",
                },
                {
                    "mean": 21.2,
                    "std": 1.1,
                    "p05": 19.39,
                    "p10": 19.79,
                    "p25": 20.46,
                    "p50": 21.2,
                    "p75": 21.94,
                    "p90": 22.61,
                    "p95": 23.01,
                    "time": "2022-02-22T03:45:00+00:00",
                },
            ],
        },
        description=(
            "Note that dict key (datapoint ID) is a string (and not an "
            " integer) due to limitations in OpenAPI. See description "
            "of the child model for additional details about the payload."
        ),
    )


class PutSummary(_BaseModel):
    """
    A summary for put operations.
    """

    objects_created: int = Field(
        ...,
        nullable=False,
        example=10,
        description="Number of objects that have been created in database.",
    )
    objects_updated: int = Field(
        ...,
        nullable=False,
        example=1,
        description="Number of objects that have been updated in database.",
    )
