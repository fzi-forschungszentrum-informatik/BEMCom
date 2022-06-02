#!/usr/bin/env python3
"""
"""
from esg.models import datapoint
from esg.test import data as td
from esg.test.generic_tests import GenericMessageSerializationTest
from esg.test.generic_tests import GenericMessageSerializationTestBEMcom


class TestDatapoint(GenericMessageSerializationTest):

    ModelClass = datapoint.Datapoint
    msgs_as_python = [m["Python"] for m in td.datapoints]
    msgs_as_jsonable = [m["JSONable"] for m in td.datapoints]
    invalid_msgs_as_jsonable = [[m["JSONable"] for m in td.invalid_datapoints]]


class TestDatapointList(GenericMessageSerializationTest):

    ModelClass = datapoint.DatapointList
    msgs_as_python = [{"__root__": [m["Python"] for m in td.datapoints]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.datapoints]]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_datapoints]


class TestDatapointById(GenericMessageSerializationTest):

    ModelClass = datapoint.DatapointById
    msgs_as_python = [
        {
            "__root__": {
                str(i): d
                for i, d in enumerate([m["Python"] for m in td.datapoints])
            }
        }
    ]
    msgs_as_jsonable = [
        {
            str(i): d
            for i, d in enumerate([m["JSONable"] for m in td.datapoints])
        }
    ]
    invalid_msgs_as_jsonable = [
        # List not a dict if ID.
        [m["JSONable"] for m in td.datapoints],
        # Dict of invalid deactivated as invalid_datapoints is empty yet
        # and thus is a valid dict!
        # {
        #     str(i): d
        #     for i, d in enumerate(
        #         [m["JSONable"] for m in td.invalid_datapoints]
        #     )
        # },
    ]


class TestValueMessage(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ValueMessage
    msgs_as_python = [m["Python"] for m in td.value_messages]
    msgs_as_jsonable = [m["JSONable"] for m in td.value_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"] for m in td.invalid_value_messages
    ]
    msgs_as_bemcom = [m["BEMCom"] for m in td.value_messages]


class TestValueMessageByDatapointId(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ValueMessageByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                str(i): m["Python"] for i, m in enumerate(td.value_messages)
            },
        }
    ]
    msgs_as_jsonable = [
        {str(i): m["JSONable"] for i, m in enumerate(td.value_messages)}
    ]
    msgs_as_bemcom = [
        {str(i): m["BEMCom"] for i, m in enumerate(td.value_messages)}
    ]
    invalid_msgs_as_jsonable = [
        # Not a dict.
        # Checks for invalid fields are already caputed in tests above.
        [[m["JSONable"] for m in td.value_messages]]
    ]


class TestValueMessageList(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ValueMessageList
    # Note the additional outer list brackets around the messages here,
    # compared to `TestValueMessage` defined above.
    # This defines that `test_messages` only contain a single element
    # which holds all the value messages defined in `testdata`.
    msgs_as_python = [{"__root__": [m["Python"] for m in td.value_messages]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.value_messages]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_value_messages]
    ]
    msgs_as_bemcom = [[m["BEMCom"] for m in td.value_messages]]


class TestValueMessageListByDatapointId(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ValueMessageListByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                "1": [m["Python"] for m in td.value_messages],
                "2": [m["Python"] for m in td.value_messages],
            },
        }
    ]
    msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.value_messages],
            "2": [m["JSONable"] for m in td.value_messages],
        }
    ]
    msgs_as_bemcom = [
        {
            "1": [m["BEMCom"] for m in td.value_messages],
            "2": [m["BEMCom"] for m in td.value_messages],
        }
    ]
    invalid_msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.invalid_value_messages],
            "2": [m["JSONable"] for m in td.invalid_value_messages],
        }
    ]


class TestValueDataFrame(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ValueDataFrame
    msgs_as_python = [
        {
            "values": {
                "1": [m["Python"]["value"] for m in td.value_messages],
                "2": [m["Python"]["value"] for m in td.value_messages],
            },
            "times": [m["Python"]["time"] for m in td.value_messages],
        }
    ]
    msgs_as_jsonable = [
        {
            "values": {
                "1": [m["JSONable"]["value"] for m in td.value_messages],
                "2": [m["JSONable"]["value"] for m in td.value_messages],
            },
            "times": [m["JSONable"]["time"] for m in td.value_messages],
        }
    ]
    msgs_as_bemcom = [
        {
            "values": {
                "1": [m["BEMCom"]["value"] for m in td.value_messages],
                "2": [m["BEMCom"]["value"] for m in td.value_messages],
            },
            "times": [m["BEMCom"]["timestamp"] for m in td.value_messages],
        }
    ]
    invalid_msgs_as_jsonable = [
        # Note that we ignore the first three invalid messages as those have
        # missing entries for `time` and/or `value`
        {
            "values": {
                "1": [
                    m["JSONable"]["value"]
                    for m in td.invalid_value_messages[3:]
                ],
                "2": [
                    m["JSONable"]["value"]
                    for m in td.invalid_value_messages[3:]
                ],
            },
            "times": [
                m["JSONable"]["time"] for m in td.invalid_value_messages[3:]
            ],
        },
        # This is invalid as the size of the index and the columns mismatch.
        {
            "values": {
                "1": [m["JSONable"]["value"] for m in td.value_messages],
                "2": [m["JSONable"]["value"] for m in td.value_messages],
            },
            "times": [m["JSONable"]["time"] for m in td.value_messages[1:]],
        },
        # This is invalid as the size of the columns mismatch.
        {
            "values": {
                "1": [m["JSONable"]["value"] for m in td.value_messages],
                "2": [m["JSONable"]["value"] for m in td.value_messages[1:]],
            },
            "times": [m["JSONable"]["time"] for m in td.value_messages],
        },
    ]


class TestSchedule(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.Schedule
    msgs_as_python = [
        {"__root__": m["Python"]["schedule"]} for m in td.schedule_messages
    ]
    msgs_as_jsonable = [m["JSONable"]["schedule"] for m in td.schedule_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"]["schedule"] for m in td.invalid_schedule_messages[2:]
    ]
    msgs_as_bemcom = [m["BEMCom"]["schedule"] for m in td.schedule_messages]


class TestScheduleMessage(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ScheduleMessage
    msgs_as_python = [m["Python"] for m in td.schedule_messages]
    msgs_as_jsonable = [m["JSONable"] for m in td.schedule_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"] for m in td.invalid_schedule_messages
    ]
    msgs_as_bemcom = [m["BEMCom"] for m in td.schedule_messages]


class TestScheduleMessageByDatapointId(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ScheduleMessageByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                str(i): m["Python"] for i, m in enumerate(td.schedule_messages)
            },
        }
    ]
    msgs_as_jsonable = [
        {str(i): m["JSONable"] for i, m in enumerate(td.schedule_messages)}
    ]
    msgs_as_bemcom = [
        {str(i): m["BEMCom"] for i, m in enumerate(td.schedule_messages)}
    ]
    invalid_msgs_as_jsonable = [
        # Not a dict.
        # Checks for invalid fields are already caputed in tests above.
        [[m["JSONable"] for m in td.schedule_messages]]
    ]


class TestScheduleMessageList(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.ScheduleMessageList
    # Note the additional outer list brackets around the messages here,
    # compared to `TestScheduleMessage` defined above.
    # This defines that `test_messages` only contain a single element
    # which holds all the value messages defined in `testdata`.
    msgs_as_python = [{"__root__": [m["Python"] for m in td.schedule_messages]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.schedule_messages]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_schedule_messages]
    ]
    msgs_as_bemcom = [[m["BEMCom"] for m in td.schedule_messages]]


class TestScheduleMessageListByDatapointId(
    GenericMessageSerializationTestBEMcom
):

    ModelClass = datapoint.ScheduleMessageListByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                "1": [m["Python"] for m in td.schedule_messages],
                "2": [m["Python"] for m in td.schedule_messages],
            },
        }
    ]
    msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.schedule_messages],
            "2": [m["JSONable"] for m in td.schedule_messages],
        }
    ]
    msgs_as_bemcom = [
        {
            "1": [m["BEMCom"] for m in td.schedule_messages],
            "2": [m["BEMCom"] for m in td.schedule_messages],
        }
    ]
    invalid_msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.invalid_schedule_messages],
            "2": [m["JSONable"] for m in td.invalid_schedule_messages],
        }
    ]


class TestSetpoint(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.Setpoint
    msgs_as_python = [
        {"__root__": m["Python"]["setpoint"]} for m in td.setpoint_messages
    ]
    msgs_as_jsonable = [m["JSONable"]["setpoint"] for m in td.setpoint_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"]["setpoint"] for m in td.invalid_setpoint_messages[2:]
    ]
    msgs_as_bemcom = [m["BEMCom"]["setpoint"] for m in td.setpoint_messages]


class TestSetpointMessage(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.SetpointMessage
    msgs_as_python = [m["Python"] for m in td.setpoint_messages]
    msgs_as_jsonable = [m["JSONable"] for m in td.setpoint_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"] for m in td.invalid_setpoint_messages
    ]
    msgs_as_bemcom = [m["BEMCom"] for m in td.setpoint_messages]


class TestSetpointMessageByDatapointId(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.SetpointMessageByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                str(i): m["Python"] for i, m in enumerate(td.setpoint_messages)
            },
        }
    ]
    msgs_as_jsonable = [
        {str(i): m["JSONable"] for i, m in enumerate(td.setpoint_messages)}
    ]
    msgs_as_bemcom = [
        {str(i): m["BEMCom"] for i, m in enumerate(td.setpoint_messages)}
    ]
    invalid_msgs_as_jsonable = [
        # Not a dict.
        # Checks for invalid fields are already caputed in tests above.
        [[m["JSONable"] for m in td.setpoint_messages]]
    ]


class TestSetpointMessageList(GenericMessageSerializationTestBEMcom):

    ModelClass = datapoint.SetpointMessageList
    # Note the additional outer list brackets around the messages here,
    # compared to `TestScheduleMessage` defined above.
    # This defines that `test_messages` only contain a single element
    # which holds all the value messages defined in `testdata`.
    msgs_as_python = [{"__root__": [m["Python"] for m in td.setpoint_messages]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.setpoint_messages]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_setpoint_messages]
    ]
    msgs_as_bemcom = [[m["BEMCom"] for m in td.setpoint_messages]]


class TestSetpointMessageListByDatapointId(
    GenericMessageSerializationTestBEMcom
):

    ModelClass = datapoint.SetpointMessageListByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                "1": [m["Python"] for m in td.setpoint_messages],
                "2": [m["Python"] for m in td.setpoint_messages],
            },
        }
    ]
    msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.setpoint_messages],
            "2": [m["JSONable"] for m in td.setpoint_messages],
        }
    ]
    msgs_as_bemcom = [
        {
            "1": [m["BEMCom"] for m in td.setpoint_messages],
            "2": [m["BEMCom"] for m in td.setpoint_messages],
        }
    ]
    invalid_msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.invalid_setpoint_messages],
            "2": [m["JSONable"] for m in td.invalid_setpoint_messages],
        }
    ]


class TestForecastMessage(GenericMessageSerializationTest):

    ModelClass = datapoint.ForecastMessage
    msgs_as_python = [m["Python"] for m in td.forecast_messages]
    msgs_as_jsonable = [m["JSONable"] for m in td.forecast_messages]
    invalid_msgs_as_jsonable = [
        m["JSONable"] for m in td.invalid_forecast_messages
    ]


class TestForecastMessageList(GenericMessageSerializationTest):

    ModelClass = datapoint.ForecastMessageList
    msgs_as_python = [{"__root__": [m["Python"] for m in td.forecast_messages]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.forecast_messages]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_forecast_messages]
    ]


class TestForecastMessageListByDatapointId(GenericMessageSerializationTest):

    ModelClass = datapoint.ForecastMessageListByDatapointId
    msgs_as_python = [
        {
            "__root__": {
                "1": [m["Python"] for m in td.forecast_messages],
                "2": [m["Python"] for m in td.forecast_messages],
            },
        }
    ]
    msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.forecast_messages],
            "2": [m["JSONable"] for m in td.forecast_messages],
        }
    ]
    invalid_msgs_as_jsonable = [
        {
            "1": [m["JSONable"] for m in td.invalid_forecast_messages],
            "2": [m["JSONable"] for m in td.invalid_forecast_messages],
        }
    ]


class TestPutSummary(GenericMessageSerializationTest):

    ModelClass = datapoint.PutSummary
    msgs_as_python = [m["Python"] for m in td.put_summaries]
    msgs_as_jsonable = [m["JSONable"] for m in td.put_summaries]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_put_summaries]
