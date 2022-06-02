#!/usr/bin/env python3
"""
"""
from datetime import datetime
from datetime import timezone

from esg.utils.timestamp import datetime_from_timestamp, datetime_to_pretty_str


class TestDatetimeFromTimestamp:
    def test_datetime_value_correct(self):
        timestamp = 1596240000000
        expected_datetime = datetime(2020, 8, 1)

        actual_datetime = datetime_from_timestamp(timestamp, tz_aware=False)
        assert actual_datetime == expected_datetime

    def test_datetime_value_with_tz_correct(self):
        timestamp = 1596240000000
        expected_datetime = datetime(2020, 8, 1, tzinfo=timezone.utc)

        actual_datetime = datetime_from_timestamp(timestamp, tz_aware=True)

        assert actual_datetime == expected_datetime


class TestDatetimeToPrettyStr:
    def test_str_value_correct(self):
        dt = datetime(2020, 1, 12, 17, 56, 2)
        expected_str = "2020-01-12 17:56:02"
        actual_str = datetime_to_pretty_str(dt)
        assert actual_str == expected_str
