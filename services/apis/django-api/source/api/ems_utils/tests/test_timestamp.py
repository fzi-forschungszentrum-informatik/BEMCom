from datetime import datetime, timezone

from django.test import TestCase

from ..timestamp import datetime_from_timestamp, datetime_to_pretty_str


class TestDatetimeFromTimestamp(TestCase):
    def test_datetime_value_correct(self):
        timestamp = 1596240000000
        expected_datetime = datetime(2020, 8, 1)

        actual_datetime = datetime_from_timestamp(timestamp, tz_aware=False)
        self.assertEqual(expected_datetime, actual_datetime)

    def test_datetime_value_with_tz_correct(self):
        timestamp = 1596240000000
        expected_datetime = datetime(2020, 8, 1, tzinfo=timezone.utc)

        actual_datetime = datetime_from_timestamp(timestamp, tz_aware=True)

        self.assertEqual(expected_datetime, actual_datetime)


class TestDatetimeToPrettyStr(TestCase):
    def test_str_value_correct(self):
        dt = datetime(2020, 1, 12, 17, 56, 2)
        expected_str = "2020-01-12 17:56:02"
        actual_str = datetime_to_pretty_str(dt)
        self.assertEqual(expected_str, actual_str)
