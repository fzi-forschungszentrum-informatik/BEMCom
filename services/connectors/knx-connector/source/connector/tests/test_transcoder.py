#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place tests for the connector specific methods here.
"""
import unittest

from xknx.dpt import DPTArray
from xknx.dpt import DPTBinary
from xknx.telegram.apci import GroupValueWrite

from ..transcoder import KnxTranscoder


class TestKnxTransoderDecodeSensorValue(unittest.TestCase):
    """
    Tests for `KnxTranscoder.decode_sensor_value` also covering
    `KnxTranscoder.__init__`.
    """

    def test_generic_bool(self):
        """
        Verify that bool datapoints can be parsed. These seems to contain all
        the same data, hence all in one test.
        """
        dpt_numbers = [
            "DPT-1",
            "DPST-1-1",
            "DPST-1-2",
            "DPST-1-3",
            "DPST-1-7",
            "DPST-1-8",
        ]
        # Mapping from telegram.payload.value.value to expected_output.
        bool_test_messages = [
            (0, False),
            (1, True),
        ]
        knx_group_address = "1/2/3"
        for dpt_number in dpt_numbers:
            knx_datapoints = {
                "sensor": {knx_group_address: dpt_number},
                "actuator": {},
            }
            knx_transcoder = KnxTranscoder(knx_datapoints=knx_datapoints)
            for value_as_knx, expected_value_as_python in bool_test_messages:
                actual_value_as_python = knx_transcoder.decode_sensor_value(
                    value_as_knx=value_as_knx,
                    knx_group_address=knx_group_address,
                )
                assert actual_value_as_python == expected_value_as_python
                # We really want a bool and `0 == False` is `True` too.
                assert type(actual_value_as_python) == bool

    def test_float_temperature(self):
        """
        A realistic temperature value. This test also checks that
        `KnxTranscoder.transcoder_by_dpt_number` automatically fetches the
        correct transcoder class.
        """
        dpt_number = "DPST-9-1"
        knx_group_address = "1/2/3"

        value_as_knx = (7, 137)
        expected_value_as_python = 19.29

        knx_datapoints = {
            "sensor": {knx_group_address: dpt_number},
            "actuator": {},
        }
        knx_transcoder = KnxTranscoder(knx_datapoints=knx_datapoints)
        actual_value_as_python = knx_transcoder.decode_sensor_value(
            value_as_knx=value_as_knx, knx_group_address=knx_group_address,
        )
        assert actual_value_as_python == expected_value_as_python


class TestKnxTransoderEncodeActuatorValue(unittest.TestCase):
    """
    Tests for `KnxTranscoder.encode_actuator_value` also covering
    `KnxTranscoder.__init__`.
    """

    def test_generic_bool(self):
        """
        Verify that bool datapoints can be decoded. These seems to contain all
        the same data, hence all in one test.
        """
        dpt_numbers = [
            "DPT-1",
            "DPST-1-1",
            "DPST-1-2",
            "DPST-1-3",
            "DPST-1-7",
            "DPST-1-8",
        ]
        # Mapping from telegram.payload.value.value to expected_output.
        bool_test_messages = [
            (False, GroupValueWrite(DPTBinary(0))),
            (True, GroupValueWrite(DPTBinary(1))),
        ]
        knx_group_address = "1/2/3"
        for dpt_number in dpt_numbers:
            knx_datapoints = {
                "sensor": {},
                "actuator": {knx_group_address: dpt_number},
            }
            knx_transcoder = KnxTranscoder(knx_datapoints=knx_datapoints)
            for value_as_python, expected_value_as_knx in bool_test_messages:
                actual_value_as_knx = knx_transcoder.encode_actuator_value(
                    value_as_python=value_as_python,
                    knx_group_address=knx_group_address,
                )
                assert actual_value_as_knx == expected_value_as_knx

    def test_float_temperature(self):
        """
        A realistic temperature value. This test also checks that
        `KnxTranscoder.transcoder_by_dpt_number` automatically fetches the
        correct transcoder class.
        """
        dpt_number = "DPST-9-1"
        knx_group_address = "4/5/6"

        value_as_python = 19.29
        expected_value_as_group_message = GroupValueWrite(DPTArray((7, 137)))

        knx_datapoints = {
            "sensor": {},
            "actuator": {knx_group_address: dpt_number},
        }
        knx_transcoder = KnxTranscoder(knx_datapoints=knx_datapoints)
        actual_value_as_group_message = knx_transcoder.encode_actuator_value(
            value_as_python=value_as_python,
            knx_group_address=knx_group_address,
        )
        assert actual_value_as_group_message == expected_value_as_group_message
